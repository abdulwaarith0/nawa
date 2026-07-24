from types import SimpleNamespace

import pytest_asyncio
from sqlalchemy import select

from nawa_api.ai.evals.intake_pipeline import EvalFixture, ai_is_gem_intake, ai_overall_intake
from nawa_api.ai.evals.schemas import HiddenGemEntry, ScoredEntry
from nawa_api.ai.prompts.hidden_gem_review import HiddenGemReview
from nawa_api.ai.prompts.score_application import Citation, CriterionScore, ScorecardDraft
from nawa_api.jobs import hidden_gem_scan as hidden_gem_scan_mod
from nawa_api.jobs import score_applications as score_applications_mod
from nawa_api.models.intake import Application, Rubric
from nawa_api.models.programs import Program, ProgramCycle


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


def _scored_entry(text: str = "great idea about water sensors") -> ScoredEntry:
    return ScoredEntry(
        application_ref="x",
        text=text,
        human_scores={"novelty": 5.0},
        human_rank_band="mid",
        language="en",
        country="QA",
        gender="f",
        origin="urban",
    )


async def test_eval_fixture_creates_and_tears_down_cleanly(bound):
    async with EvalFixture() as fixture:
        program_id, cycle_id, rubric_id = fixture.program_id, fixture.cycle_id, fixture.rubric_id
        assert program_id is not None
        program = (
            await bound.execute(select(Program).where(Program.id == program_id))
        ).scalar_one_or_none()
        assert program is not None

    assert (
        await bound.execute(select(Program).where(Program.id == program_id))
    ).scalar_one_or_none() is None
    assert (
        await bound.execute(select(ProgramCycle).where(ProgramCycle.id == cycle_id))
    ).scalar_one_or_none() is None
    assert (
        await bound.execute(select(Rubric).where(Rubric.id == rubric_id))
    ).scalar_one_or_none() is None


async def test_ai_overall_intake_via_real_mock_grounds_citations_and_scores(bound):
    # No monkeypatching: MockLLMProvider grounds each criterion's citation in
    # a real "answer:<key>" quote from the rendered application text
    # (ai/providers/mock_provider.py), so validate_scorecard now accepts it
    # on the first attempt and a real, deterministic (fingerprint-seeded)
    # nonzero score comes back — this used to legitimately fall back to 0.0
    # before that grounding existed.
    entry = _scored_entry()
    async with EvalFixture() as fixture:
        score = await ai_overall_intake(entry, fixture=fixture, provider_name="mock")
        assert score == 22.0
        remaining = (
            await bound.execute(
                select(Application).where(Application.cycle_id == fixture.cycle_id)
            )
        ).scalars().all()
        assert remaining == []  # torn down immediately after this one entry


async def test_ai_overall_intake_reads_back_a_real_score_on_success(bound, monkeypatch):
    entry = _scored_entry("great idea about water sensors")

    async def fake_structured(request, schema, **kwargs):
        draft = ScorecardDraft(
            criteria=[
                CriterionScore(
                    criterion_key=key,
                    score=8,
                    rationale_ar="م",
                    rationale_en="Solid.",
                    citations=[Citation(source="answer:idea", quote="water sensors")],
                )
                for key in ("novelty", "feasibility", "capability", "regional_impact")
            ],
            rationale_ar="عام",
            rationale_en="Overall solid.",
            confidence=0.8,
        )
        return draft, SimpleNamespace(model="claude-opus-4-8")

    monkeypatch.setattr(score_applications_mod.gateway, "complete_structured", fake_structured)

    async with EvalFixture() as fixture:
        score = await ai_overall_intake(entry, fixture=fixture, provider_name="mock")
        assert score == 80.0  # every criterion scores 8/10 -> 100% of every weight
        remaining = (
            await bound.execute(
                select(Application).where(Application.cycle_id == fixture.cycle_id)
            )
        ).scalars().all()
        assert remaining == []  # torn down even after a successful score


async def test_ai_is_gem_intake_via_real_mock_grounds_citations_and_cleans_up(bound):
    # Grounded citations mean validate_hidden_gem_review now accepts the
    # mock's output too; `is_hidden_gem` itself is fingerprint-varied (see
    # mock_provider.py's `_ground_citations`) rather than always True.
    entry = HiddenGemEntry(application_ref="g1", text="weak prose, strong idea", is_gem=True)
    async with EvalFixture() as fixture:
        result = await ai_is_gem_intake(entry, fixture=fixture, provider_name="mock")
        assert result is True
        remaining = (
            await bound.execute(
                select(Application).where(Application.cycle_id == fixture.cycle_id)
            )
        ).scalars().all()
        assert remaining == []


async def test_ai_is_gem_intake_reads_back_true_on_success(bound, monkeypatch):
    entry = HiddenGemEntry(application_ref="g1", text="water sensors idea", is_gem=True)

    async def fake_structured(request, schema, **kwargs):
        review = HiddenGemReview(
            is_hidden_gem=True,
            reason_ar="سبب",
            reason_en="Strong idea, weak prose.",
            citations=[Citation(source="answer:idea", quote="water sensors")],
        )
        return review, SimpleNamespace(model="claude-opus-4-8")

    monkeypatch.setattr(hidden_gem_scan_mod.gateway, "complete_structured", fake_structured)

    async with EvalFixture() as fixture:
        result = await ai_is_gem_intake(entry, fixture=fixture, provider_name="mock")
        assert result is True
