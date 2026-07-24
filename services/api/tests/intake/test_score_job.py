import uuid
from types import SimpleNamespace

import pytest_asyncio
from sqlalchemy import select

from nawa_api.ai.prompts.score_application import Citation, CriterionScore, ScorecardDraft
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.list_scorecards_for_application_db import (
    list_scorecards_for_application_db,
)
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.jobs import score_applications as score_mod
from nawa_api.jobs.score_applications import score_application
from nawa_api.models.intake import Application

_CRITERIA = [
    {"key": "novelty", "label_en": "Novelty", "weight": 0.6, "scale_max": 10},
    {"key": "feasibility", "label_en": "Feasibility", "weight": 0.4, "scale_max": 10},
]


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _rubric_and_application(session, *, answers):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", name_en="P", kind="competition", session=session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=session
    )
    rubric = await create_rubric_db(
        program_id=program.id, version=1, criteria=_CRITERIA, name_en="R", session=session
    )
    app = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="Amina",
        applicant_email="a@x.io",
        source_language="en",
        original_answers=answers,
        session=session,
    )
    await session.commit()
    return rubric, app


async def _fresh(session, app_id):
    session.expire_all()
    return (
        await session.execute(select(Application).where(Application.id == app_id))
    ).scalar_one()


def _valid_draft() -> ScorecardDraft:
    return ScorecardDraft(
        criteria=[
            CriterionScore(
                criterion_key="novelty",
                score=8,
                rationale_ar="ملاحظة",
                rationale_en="Solid novelty.",
                citations=[Citation(source="answer:idea", quote="low-cost water sensors")],
            ),
            CriterionScore(
                criterion_key="feasibility",
                score=6,
                rationale_ar="ملاحظة",
                rationale_en="Feasible with caveats.",
                citations=[Citation(source="answer:idea", quote="low-cost water sensors")],
            ),
        ],
        rationale_ar="عام",
        rationale_en="Overall solid.",
        confidence=0.75,
    )


def _hallucinated_draft() -> ScorecardDraft:
    return ScorecardDraft(
        criteria=[
            CriterionScore(
                criterion_key="novelty",
                score=8,
                rationale_ar="م",
                rationale_en="N",
                citations=[Citation(source="answer:idea", quote="never actually said this")],
            ),
            CriterionScore(
                criterion_key="feasibility",
                score=6,
                rationale_ar="م",
                rationale_en="F",
                citations=[Citation(source="answer:idea", quote="never actually said this")],
            ),
        ],
        rationale_ar="ر",
        rationale_en="R",
        confidence=0.5,
    )


async def test_score_happy_path_persists_scorecard_and_criteria(bound, monkeypatch):
    rubric, app = await _rubric_and_application(
        bound, answers={"idea": "we build low-cost water sensors for farms"}
    )

    async def fake_structured(request, schema, **kwargs):
        return _valid_draft(), SimpleNamespace(model="claude-opus-4-8")

    monkeypatch.setattr(score_mod.gateway, "complete_structured", fake_structured)

    result = await score_application(application_id=str(app.id), rubric_id=str(rubric.id))
    assert result == "scored"

    row = await _fresh(bound, app.id)
    assert row.status == "scored"
    # weighted total: (8/10*0.6 + 6/10*0.4) * 100 = (0.48 + 0.24) * 100 = 72.0
    assert row.ai_total_score == 72.0
    assert row.scored_at is not None

    scorecards = await list_scorecards_for_application_db(application_id=app.id, session=bound)
    assert len(scorecards) == 1
    assert scorecards[0].total_score == 72.0
    assert scorecards[0].source == "ai"
    assert scorecards[0].prompt_version == "v2"
    assert scorecards[0].model == "claude-opus-4-8"


async def test_score_missing_application_is_noop(bound):
    rubric, _app = await _rubric_and_application(bound, answers={"idea": "x"})
    assert (
        await score_application(application_id=str(uuid.uuid4()), rubric_id=str(rubric.id))
        == "missing"
    )


async def test_score_missing_rubric_is_noop(bound):
    _rubric, app = await _rubric_and_application(bound, answers={"idea": "x"})
    assert (
        await score_application(application_id=str(app.id), rubric_id=str(uuid.uuid4()))
        == "missing"
    )


async def test_score_repair_loop_retries_after_hallucination(bound, monkeypatch):
    rubric, app = await _rubric_and_application(
        bound, answers={"idea": "we build low-cost water sensors for farms"}
    )

    calls = {"n": 0}

    async def fake_structured(request, schema, **kwargs):
        calls["n"] += 1
        draft = _hallucinated_draft() if calls["n"] == 1 else _valid_draft()
        return draft, SimpleNamespace(model="claude-opus-4-8")

    monkeypatch.setattr(score_mod.gateway, "complete_structured", fake_structured)

    result = await score_application(application_id=str(app.id), rubric_id=str(rubric.id))
    assert result == "scored"
    assert calls["n"] == 2

    row = await _fresh(bound, app.id)
    assert row.status == "scored"


async def test_score_exhausts_repair_attempts_leaves_status_unchanged(bound, monkeypatch):
    rubric, app = await _rubric_and_application(
        bound, answers={"idea": "we build low-cost water sensors for farms"}
    )

    calls = {"n": 0}

    async def fake_structured(request, schema, **kwargs):
        calls["n"] += 1
        return _hallucinated_draft(), SimpleNamespace(model="claude-opus-4-8")

    monkeypatch.setattr(score_mod.gateway, "complete_structured", fake_structured)

    result = await score_application(application_id=str(app.id), rubric_id=str(rubric.id))
    assert result == "score_failed"
    assert calls["n"] == score_mod.SCORE_REPAIR_ATTEMPTS

    row = await _fresh(bound, app.id)
    assert row.status == "submitted"  # never dropped, never advanced on a bad draft
    assert row.ai_total_score is None

    scorecards = await list_scorecards_for_application_db(application_id=app.id, session=bound)
    assert scorecards == []


def test_application_text_includes_summary_when_present():
    application = SimpleNamespace(
        original_answers={"idea": "water sensors"}, summary="A concise AI summary."
    )
    text = score_mod._application_text(application)
    assert "idea: water sensors" in text
    assert "summary: A concise AI summary." in text


async def test_score_via_real_mock_provider_fails_validation_and_is_retriable(bound):
    # No monkeypatch on the gateway here: MockLLMProvider synthesizes structurally-valid
    # but semantically-meaningless criterion keys/quotes, so validate_scorecard rejects
    # every attempt and the job reports score_failed without touching application status.
    rubric, app = await _rubric_and_application(
        bound, answers={"idea": "we build low-cost water sensors for farms"}
    )

    result = await score_application(application_id=str(app.id), rubric_id=str(rubric.id))
    assert result == "score_failed"

    row = await _fresh(bound, app.id)
    assert row.status == "submitted"
