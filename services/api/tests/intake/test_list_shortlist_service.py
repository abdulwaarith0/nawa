import uuid

import pytest
import pytest_asyncio

from nawa_api.contracts.errors import ApiError
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.create_scorecard_criterion_db import create_scorecard_criterion_db
from nawa_api.db.intake.create_scorecard_db import create_scorecard_db
from nawa_api.db.intake.update_application_scoring_db import update_application_scoring_db
from nawa_api.db.intake.update_scorecard_hidden_gem_db import update_scorecard_hidden_gem_db
from nawa_api.db.intake.upsert_dedup_match_db import upsert_dedup_match_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.models.intake import Application
from nawa_api.runtime.redis import get_redis
from nawa_api.services.intake import list_shortlist as list_shortlist_mod
from nawa_api.services.intake.list_shortlist import cache_key, list_shortlist

_CRITERIA = [{"key": "novelty", "weight": 1.0, "scale_max": 10}]


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _cycle_with_rubric(session, *, rubric_status="active"):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=session
    )
    rubric = await create_rubric_db(
        program_id=program.id,
        version=1,
        criteria=_CRITERIA,
        name_en="R",
        status=rubric_status,
        session=session,
    )
    return cycle, rubric


async def _scored_application(session, *, cycle_id, rubric_id, total_score):
    app = await create_application_db(
        cycle_id=cycle_id,
        applicant_name="Amina",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "great idea"},
        session=session,
    )
    await update_application_scoring_db(
        application_id=app.id, total_score=total_score, session=session
    )
    scorecard = await create_scorecard_db(
        application_id=app.id,
        rubric_id=rubric_id,
        rubric_version=1,
        prompt_version="v2",
        source="ai",
        total_score=total_score,
        session=session,
    )
    await create_scorecard_criterion_db(
        scorecard_id=scorecard.id,
        criterion_key="novelty",
        score=7.0,
        weight=1.0,
        session=session,
    )
    return app, scorecard


async def test_missing_cycle_raises_not_found(bound):
    with pytest.raises(ApiError):
        await list_shortlist(cycle_id=uuid.uuid4())


async def test_no_active_rubric_returns_empty(bound):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=bound
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=bound
    )
    await bound.commit()
    assert await list_shortlist(cycle_id=cycle.id) == []


async def test_row_shape_and_hidden_gem_flag(bound):
    cycle, rubric = await _cycle_with_rubric(bound)
    _app, scorecard = await _scored_application(
        bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=42
    )
    await update_scorecard_hidden_gem_db(
        scorecard_id=scorecard.id,
        hidden_gem=True,
        hidden_gem_reason_ar="س",
        hidden_gem_reason_en="Strong idea.",
        session=bound,
    )
    await bound.commit()

    items = await list_shortlist(cycle_id=cycle.id)
    assert len(items) == 1
    row = items[0]
    assert row["rank"] == 1
    assert row["total_score"] == 42
    assert row["hidden_gem"] is True
    assert row["dedup_pending"] is False
    assert row["decision"] == "undecided"
    assert row["criteria"] == [{"criterion_key": "novelty", "score": 7.0, "weight": 1.0}]


async def test_score_band_string_is_parsed(bound):
    cycle, rubric = await _cycle_with_rubric(bound)
    await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10)
    await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    await bound.commit()

    items = await list_shortlist(cycle_id=cycle.id, score_band="80-100")
    assert len(items) == 1
    assert items[0]["total_score"] == 90


async def test_invalid_decision_value_is_ignored_not_a_crash(bound):
    cycle, rubric = await _cycle_with_rubric(bound)
    await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10)
    await bound.commit()

    items = await list_shortlist(cycle_id=cycle.id, decision="not-a-real-state")
    assert len(items) == 1  # falls back to no decision filter rather than raising


async def test_unknown_flags_are_dropped_not_a_crash(bound):
    cycle, rubric = await _cycle_with_rubric(bound)
    await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10)
    await bound.commit()

    items = await list_shortlist(cycle_id=cycle.id, flags=frozenset({"not_a_real_flag"}))
    assert len(items) == 1  # the bogus flag is simply not applied


async def test_result_is_cached_until_invalidated(bound, monkeypatch):
    cycle, rubric = await _cycle_with_rubric(bound)
    await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10)
    await bound.commit()

    first = await list_shortlist(cycle_id=cycle.id)
    assert len(first) == 1

    calls = {"n": 0}
    real_db_call = list_shortlist_mod.list_shortlist_db

    async def counting_call(*args, **kwargs):
        calls["n"] += 1
        return await real_db_call(*args, **kwargs)

    monkeypatch.setattr(list_shortlist_mod, "list_shortlist_db", counting_call)
    second = await list_shortlist(cycle_id=cycle.id)
    assert second == first
    assert calls["n"] == 0  # served from cache, the db layer was never touched


async def test_empty_result_is_not_cached(bound):
    cycle, _rubric = await _cycle_with_rubric(bound)
    await bound.commit()

    items = await list_shortlist(cycle_id=cycle.id)
    assert items == []
    key = cache_key(
        cycle_id=cycle.id,
        score_band=None,
        criterion=None,
        criterion_min=None,
        flags=frozenset(),
        language=None,
        country=None,
        decision=None,
        q=None,
        limit=100,
        offset=0,
    )
    assert await get_redis().get(key) is None


async def test_dedup_pending_flag_surfaced_for_both_sides(bound):
    cycle, rubric = await _cycle_with_rubric(bound)
    app_a, _card_a = await _scored_application(
        bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10
    )
    app_b, _card_b = await _scored_application(
        bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=20
    )
    await upsert_dedup_match_db(
        application_id=app_a.id, matched_application_id=app_b.id, similarity=0.9, session=bound
    )
    await bound.commit()

    items = await list_shortlist(cycle_id=cycle.id)
    assert {i["application_id"]: i["dedup_pending"] for i in items} == {
        str(app_a.id): True,
        str(app_b.id): True,
    }


async def test_decision_states_surfaced_by_status(bound):
    from sqlalchemy import update

    cycle, rubric = await _cycle_with_rubric(bound)
    shortlisted, _c1 = await _scored_application(
        bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10
    )
    waitlisted, _c2 = await _scored_application(
        bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=20
    )
    decided, _c3 = await _scored_application(
        bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=30
    )
    for app_id, status in (
        (shortlisted.id, "shortlisted"),
        (waitlisted.id, "waitlisted"),
        (decided.id, "decided"),
    ):
        stmt = update(Application).where(Application.id == app_id).values(status=status)
        await bound.execute(stmt)
    await bound.commit()

    items = await list_shortlist(cycle_id=cycle.id)
    decisions_by_id = {i["application_id"]: i["decision"] for i in items}
    assert decisions_by_id[str(shortlisted.id)] == "shortlist"
    assert decisions_by_id[str(waitlisted.id)] == "waitlist"
    assert decisions_by_id[str(decided.id)] == "decided"  # no decisions row -> falls back
