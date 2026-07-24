import uuid

import pytest_asyncio

from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.upsert_dedup_match_db import upsert_dedup_match_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.services.intake import list_dedup_matches as list_dedup_matches_mod
from nawa_api.services.intake.list_dedup_matches import list_dedup_matches


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _application(session, *, cycle_id):
    return await create_application_db(
        cycle_id=cycle_id,
        applicant_name="A",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "x"},
        session=session,
    )


async def test_returns_empty_for_no_matches(bound):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=bound
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=bound
    )
    app = await _application(bound, cycle_id=cycle.id)
    await bound.commit()
    assert await list_dedup_matches(application_id=app.id) == []


async def test_returns_matches_and_is_cached(bound, monkeypatch):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=bound
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=bound
    )
    app_a = await _application(bound, cycle_id=cycle.id)
    app_b = await _application(bound, cycle_id=cycle.id)
    await upsert_dedup_match_db(
        application_id=app_a.id, matched_application_id=app_b.id, similarity=0.9, session=bound
    )
    await bound.commit()

    first = await list_dedup_matches(application_id=app_a.id)
    assert len(first) == 1
    assert first[0]["matched_application_id"] == str(app_b.id)

    async def fail_if_called(**kwargs):
        raise AssertionError("must not touch the db — the cache should have served this")

    monkeypatch.setattr(list_dedup_matches_mod, "list_dedup_matches_db", fail_if_called)
    second = await list_dedup_matches(application_id=app_a.id)
    assert second == first
