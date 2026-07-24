import uuid
from types import SimpleNamespace

import pytest_asyncio
from sqlalchemy import select

from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.create_scorecard_db import create_scorecard_db
from nawa_api.db.intake.update_application_scoring_db import update_application_scoring_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.jobs import hidden_gem_scan as hidden_gem_scan_mod
from nawa_api.jobs.hidden_gem_scan import HIDDEN_GEM_BAND, _application_text, hidden_gem_scan
from nawa_api.models.intake import Scorecard

_CRITERIA = [{"key": "novelty", "label_en": "Novelty", "weight": 1.0, "scale_max": 10}]


def test_application_text_includes_summary_when_present():
    application = SimpleNamespace(
        original_answers={"idea": "water sensors"}, summary="A concise AI summary."
    )
    text = _application_text(application)
    assert "idea: water sensors" in text
    assert "summary: A concise AI summary." in text


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _cycle_with_rubric(session):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", name_en="P", kind="competition", session=session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=session
    )
    rubric = await create_rubric_db(
        program_id=program.id, version=1, criteria=_CRITERIA, name_en="R", session=session
    )
    return cycle, rubric


async def _scored_application(session, *, cycle_id, rubric_id, total_score, answers=None):
    app = await create_application_db(
        cycle_id=cycle_id,
        applicant_name="Amina",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers=answers or {"idea": "we build low-cost water sensors for farms"},
        session=session,
    )
    await update_application_scoring_db(
        application_id=app.id, total_score=total_score, session=session
    )
    await create_scorecard_db(
        application_id=app.id,
        rubric_id=rubric_id,
        rubric_version=1,
        prompt_version="v2",
        source="ai",
        total_score=total_score,
        session=session,
    )
    return app


def _valid_review(*, is_hidden_gem: bool):
    from nawa_api.ai.prompts.hidden_gem_review import HiddenGemReview
    from nawa_api.ai.prompts.score_application import Citation

    return HiddenGemReview(
        is_hidden_gem=is_hidden_gem,
        reason_ar="سبب",
        reason_en="A strong idea in weak prose.",
        citations=[Citation(source="answer:idea", quote="low-cost water sensors")],
    )


def _hallucinated_review():
    from nawa_api.ai.prompts.hidden_gem_review import HiddenGemReview
    from nawa_api.ai.prompts.score_application import Citation

    return HiddenGemReview(
        is_hidden_gem=True,
        reason_ar="سبب",
        reason_en="Reason",
        citations=[Citation(source="answer:idea", quote="never actually said this")],
    )


async def _scorecard_for(session, application_id):
    # populate_existing: the scorecard was created via this same `bound` session
    # (so it's already identity-mapped) but updated by hidden_gem_scan through a
    # DIFFERENT session — without this, the stale in-memory copy would either
    # read old values or, once expired, trigger a sync lazy-load that an async
    # session can't service outside a greenlet context.
    stmt = (
        select(Scorecard)
        .where(Scorecard.application_id == application_id, Scorecard.source == "ai")
        .execution_options(populate_existing=True)
    )
    return (await session.execute(stmt)).scalar_one()


async def test_flags_bottom_band_and_persists_reason(bound, monkeypatch):
    cycle, rubric = await _cycle_with_rubric(bound)
    low = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10)
    mid = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=50)
    high = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    await bound.commit()
    low_id, mid_id, high_id = low.id, mid.id, high.id

    async def fake_structured(request, schema, **kwargs):
        return _valid_review(is_hidden_gem=True), SimpleNamespace(model="claude-opus-4-8")

    monkeypatch.setattr(hidden_gem_scan_mod.gateway, "complete_structured", fake_structured)

    result = await hidden_gem_scan(cycle_id=str(cycle.id))
    # ceil(3 * 0.4) == 2 -> the two lowest scorers only
    assert result == {"total": 2, "flagged": 2, "failed": 0}

    low_card = await _scorecard_for(bound, low_id)
    mid_card = await _scorecard_for(bound, mid_id)
    high_card = await _scorecard_for(bound, high_id)
    assert low_card.hidden_gem is True
    assert low_card.hidden_gem_reason_en == "A strong idea in weak prose."
    assert mid_card.hidden_gem is True  # second-lowest, also inside ceil(3*0.4)=2
    assert high_card.hidden_gem is False  # never reviewed — not in the bottom band


async def test_non_gem_review_persists_false(bound, monkeypatch):
    cycle, rubric = await _cycle_with_rubric(bound)
    app = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10)
    await bound.commit()
    app_id = app.id

    async def fake_structured(request, schema, **kwargs):
        return _valid_review(is_hidden_gem=False), SimpleNamespace(model="mock")

    monkeypatch.setattr(hidden_gem_scan_mod.gateway, "complete_structured", fake_structured)

    result = await hidden_gem_scan(cycle_id=str(cycle.id))
    assert result == {"total": 1, "flagged": 0, "failed": 0}
    card = await _scorecard_for(bound, app_id)
    assert card.hidden_gem is False
    assert card.hidden_gem_reason_en == "A strong idea in weak prose."


async def test_repair_loop_retries_after_hallucination(bound, monkeypatch):
    cycle, rubric = await _cycle_with_rubric(bound)
    app = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10)
    await bound.commit()
    app_id = app.id

    calls = {"n": 0}

    async def fake_structured(request, schema, **kwargs):
        calls["n"] += 1
        review = _hallucinated_review() if calls["n"] == 1 else _valid_review(is_hidden_gem=True)
        return review, SimpleNamespace(model="mock")

    monkeypatch.setattr(hidden_gem_scan_mod.gateway, "complete_structured", fake_structured)

    result = await hidden_gem_scan(cycle_id=str(cycle.id))
    assert result == {"total": 1, "flagged": 1, "failed": 0}
    assert calls["n"] == 2
    card = await _scorecard_for(bound, app_id)
    assert card.hidden_gem is True


async def test_repair_exhaustion_leaves_scorecard_untouched(bound, monkeypatch):
    cycle, rubric = await _cycle_with_rubric(bound)
    app = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10)
    await bound.commit()
    app_id = app.id

    async def fake_structured(request, schema, **kwargs):
        return _hallucinated_review(), SimpleNamespace(model="mock")

    monkeypatch.setattr(hidden_gem_scan_mod.gateway, "complete_structured", fake_structured)

    result = await hidden_gem_scan(cycle_id=str(cycle.id))
    assert result == {"total": 1, "flagged": 0, "failed": 1}
    card = await _scorecard_for(bound, app_id)
    assert card.hidden_gem is False  # never persisted a hallucinated review
    assert card.hidden_gem_reason_en is None


async def test_application_without_an_ai_scorecard_is_skipped(bound, monkeypatch):
    cycle, _rubric = await _cycle_with_rubric(bound)
    # status='scored' but no scorecard row at all — shouldn't happen in practice,
    # but the job must degrade gracefully rather than crash on a missing scorecard.
    app = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="Amina",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "water sensors"},
        session=bound,
    )
    await update_application_scoring_db(application_id=app.id, total_score=10.0, session=bound)
    await bound.commit()

    async def fake_structured(request, schema, **kwargs):
        raise AssertionError("must not be called — there is no scorecard to update")

    monkeypatch.setattr(hidden_gem_scan_mod.gateway, "complete_structured", fake_structured)

    result = await hidden_gem_scan(cycle_id=str(cycle.id))
    assert result == {"total": 1, "flagged": 0, "failed": 0}


async def test_no_scored_applications_is_a_noop(bound):
    cycle, _rubric = await _cycle_with_rubric(bound)
    await bound.commit()
    assert await hidden_gem_scan(cycle_id=str(cycle.id)) == {
        "total": 0,
        "flagged": 0,
        "failed": 0,
    }


async def test_pages_through_more_than_one_hundred_scored_applications(bound, monkeypatch):
    cycle, rubric = await _cycle_with_rubric(bound)
    for i in range(105):
        await _scored_application(
            bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=float(i)
        )
    await bound.commit()

    async def fake_structured(request, schema, **kwargs):
        return _valid_review(is_hidden_gem=False), SimpleNamespace(model="mock")

    monkeypatch.setattr(hidden_gem_scan_mod.gateway, "complete_structured", fake_structured)

    result = await hidden_gem_scan(cycle_id=str(cycle.id))
    assert result["total"] == 42  # ceil(105 * 0.4) == 42, spanning both pages of applications
    assert HIDDEN_GEM_BAND == 0.4
