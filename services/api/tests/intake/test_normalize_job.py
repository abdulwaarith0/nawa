import uuid

import pytest_asyncio
from sqlalchemy import select

from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.jobs.normalize_applications import normalize_application
from nawa_api.models.intake import Application
from nawa_api.runtime.redis import get_redis


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _application(session, *, answers):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", name_en="P", kind="competition", session=session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id,
        slug=f"c-{uuid.uuid4().hex[:8]}",
        name_en="C",
        status="screening",
        session=session,
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
    return app


async def _fresh(session, app_id):
    session.expire_all()
    return (
        await session.execute(select(Application).where(Application.id == app_id))
    ).scalar_one()


async def test_normalize_happy_path(bound):
    answers = {"idea": "we build low-cost water sensors for farms"}
    app = await _application(bound, answers=answers)

    result = await normalize_application(application_id=str(app.id))
    assert result == "normalized"

    row = await _fresh(bound, app.id)
    assert row.status == "normalized"
    assert row.source_language in ("ar", "en", "fr")
    assert set(row.normalized) >= {"title", "summary", "problem", "solution"}
    assert row.title is not None and row.summary is not None
    assert row.normalized_at is not None
    assert row.original_answers == answers  # sacred — byte-identical


async def test_normalize_failure_marks_failed_not_dropped(bound):
    answers = {"idea": "great idea __MOCK_REFUSAL__ here"}
    app = await _application(bound, answers=answers)

    result = await normalize_application(application_id=str(app.id))
    assert result == "normalize_failed"

    row = await _fresh(bound, app.id)
    assert row.status == "normalize_failed"
    assert "error" in row.normalized
    assert row.original_answers == answers  # never dropped, never modified


async def test_normalize_missing_application_is_noop(bound):
    assert await normalize_application(application_id=str(uuid.uuid4())) == "missing"


async def test_progress_hash_increments(bound):
    app = await _application(bound, answers={"idea": "sensors"})
    upload_id = uuid.uuid4()
    await get_redis().delete(f"jobs:intake:upload:{upload_id}:progress")
    await normalize_application(application_id=str(app.id), upload_id=str(upload_id))
    done = await get_redis().hget(f"jobs:intake:upload:{upload_id}:progress", "done")
    assert int(done) == 1
