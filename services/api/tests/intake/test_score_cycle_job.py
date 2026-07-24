import uuid

import pytest_asyncio
from sqlalchemy import select

from nawa_api.ai import budget
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.update_application_normalization_db import (
    update_application_normalization_db,
)
from nawa_api.db.intake.update_application_scoring_db import update_application_scoring_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.jobs import score_cycle as score_cycle_mod
from nawa_api.jobs.score_cycle import progress_key, score_cycle
from nawa_api.models.intake import Application
from nawa_api.runtime.redis import get_redis

_CRITERIA = [{"key": "novelty", "label_en": "Novelty", "weight": 1.0, "scale_max": 10}]


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _cycle_with_rubric(session, *, rubric_status="active"):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", name_en="P", kind="competition", session=session
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
    return program, cycle, rubric


async def _application(session, *, cycle_id, status="normalized"):
    app = await create_application_db(
        cycle_id=cycle_id,
        applicant_name="Amina",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "great idea"},
        session=session,
    )
    if status in ("normalized", "scored"):
        await update_application_normalization_db(
            application_id=app.id,
            source_language="en",
            normalized={"title": "T"},
            title="T",
            summary="S",
            session=session,
        )
    if status == "scored":
        await update_application_scoring_db(
            application_id=app.id, total_score=50.0, session=session
        )
    return app


async def _statuses(session, ids):
    session.expire_all()
    rows = (await session.execute(select(Application).where(Application.id.in_(ids)))).scalars()
    return {row.id: row.status for row in rows}


async def test_score_cycle_scores_every_normalized_application(bound, monkeypatch):
    _program, cycle, _rubric = await _cycle_with_rubric(bound)
    app_a = await _application(bound, cycle_id=cycle.id)
    app_b = await _application(bound, cycle_id=cycle.id)
    await bound.commit()

    async def fake_score(*, application_id, rubric_id, cycle_id):
        return "scored"

    monkeypatch.setattr(score_cycle_mod, "score_application", fake_score)

    result = await score_cycle(cycle_id=str(cycle.id))
    assert result == {"total": 2, "done": 2, "failed": 0, "stopped_reason": None}

    counts = await get_redis().hgetall(progress_key(cycle.id))
    assert counts["total"] == "2"
    assert counts["done"] == "2"
    assert "stopped_reason" not in counts

    statuses = await _statuses(bound, [app_a.id, app_b.id])
    assert set(statuses.values()) == {"normalized"}  # fake_score never touched the DB


async def test_score_cycle_counts_failures_separately(bound, monkeypatch):
    _program, cycle, _rubric = await _cycle_with_rubric(bound)
    await _application(bound, cycle_id=cycle.id)
    await _application(bound, cycle_id=cycle.id)
    await bound.commit()

    calls = {"n": 0}

    async def fake_score(*, application_id, rubric_id, cycle_id):
        calls["n"] += 1
        return "scored" if calls["n"] == 1 else "score_failed"

    monkeypatch.setattr(score_cycle_mod, "score_application", fake_score)

    result = await score_cycle(cycle_id=str(cycle.id))
    assert result == {"total": 2, "done": 1, "failed": 1, "stopped_reason": None}


async def test_score_cycle_rescore_targets_already_scored_applications(bound, monkeypatch):
    _program, cycle, _rubric = await _cycle_with_rubric(bound)
    await _application(bound, cycle_id=cycle.id, status="normalized")
    scored_app = await _application(bound, cycle_id=cycle.id, status="scored")
    await bound.commit()

    seen_ids = []

    async def fake_score(*, application_id, rubric_id, cycle_id):
        seen_ids.append(application_id)
        return "scored"

    monkeypatch.setattr(score_cycle_mod, "score_application", fake_score)

    result = await score_cycle(cycle_id=str(cycle.id), rescore=True)
    assert result["total"] == 1
    assert seen_ids == [str(scored_app.id)]


async def test_score_cycle_pages_through_more_than_one_hundred_applications(bound, monkeypatch):
    # list_applications_db caps a single page at 100 rows — the fan-out must page
    # through the full target set before scoring starts, not just score page one.
    _program, cycle, _rubric = await _cycle_with_rubric(bound)
    for _ in range(105):
        await _application(bound, cycle_id=cycle.id)
    await bound.commit()

    async def fake_score(*, application_id, rubric_id, cycle_id):
        return "scored"

    monkeypatch.setattr(score_cycle_mod, "score_application", fake_score)

    result = await score_cycle(cycle_id=str(cycle.id))
    assert result == {"total": 105, "done": 105, "failed": 0, "stopped_reason": None}


async def test_score_cycle_missing_cycle_reports_stopped_reason(bound):
    result = await score_cycle(cycle_id=str(uuid.uuid4()))
    assert result == {"total": 0, "done": 0, "failed": 0, "stopped_reason": "cycle_not_found"}


async def test_score_cycle_missing_active_rubric_reports_stopped_reason(bound):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", name_en="P", kind="competition", session=bound
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=bound
    )
    await bound.commit()

    result = await score_cycle(cycle_id=str(cycle.id))
    assert result == {"total": 0, "done": 0, "failed": 0, "stopped_reason": "no_active_rubric"}


async def test_score_cycle_stops_early_on_budget_exhaustion(bound, monkeypatch):
    _program, cycle, _rubric = await _cycle_with_rubric(bound)
    app_a = await _application(bound, cycle_id=cycle.id)
    app_b = await _application(bound, cycle_id=cycle.id)
    await bound.commit()

    async def fake_score(*, application_id, rubric_id, cycle_id):
        raise AssertionError("must not be called once the budget is exhausted")

    async def fake_get_spend(cycle_id):
        return 10_000.0

    monkeypatch.setattr(score_cycle_mod, "score_application", fake_score)
    monkeypatch.setattr(budget, "get_spend", fake_get_spend)

    result = await score_cycle(cycle_id=str(cycle.id))
    assert result["stopped_reason"] == "budget_exceeded"
    assert result["done"] == 0
    assert result["failed"] == 0

    statuses = await _statuses(bound, [app_a.id, app_b.id])
    assert set(statuses.values()) == {"normalized"}  # untouched, retriable
