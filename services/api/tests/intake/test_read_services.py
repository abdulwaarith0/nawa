import uuid

import pytest_asyncio

from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.runtime.redis import get_redis
from nawa_api.services.intake import get_application as get_app_mod
from nawa_api.services.intake import get_rubric as get_rubric_mod
from nawa_api.services.intake import list_rubrics as list_rubrics_mod
from nawa_api.services.intake.get_application import get_application
from nawa_api.services.intake.get_rubric import get_rubric
from nawa_api.services.intake.list_applications import list_applications
from nawa_api.services.intake.list_rubrics import list_rubrics

_CRITERIA = [
    {
        "key": "novelty",
        "label_ar": "الابتكار",
        "label_en": "Novelty",
        "weight": 1.0,
        "scale_max": 10,
    },
]


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _program(session, slug):
    return await create_program_db(
        slug=slug, name_ar="برنامج", name_en="Program", kind="competition", session=session
    )


async def _cycle(session, program_id, slug):
    return await create_program_cycle_db(
        program_id=program_id,
        slug=slug,
        name_ar="دورة",
        name_en="Cycle",
        status="screening",
        session=session,
    )


async def _application(session, cycle_id, *, email="a@x.io"):
    return await create_application_db(
        cycle_id=cycle_id,
        applicant_name="Amina",
        applicant_email=email,
        source_language="en",
        original_answers={"q1": "we build things"},
        session=session,
    )


async def test_get_rubric_returns_dto(bound):
    program = await _program(bound, f"p-{uuid.uuid4().hex[:8]}")
    rubric = await create_rubric_db(
        program_id=program.id,
        version=1,
        criteria=_CRITERIA,
        name_en="R",
        status="active",
        session=bound,
    )
    await bound.commit()

    dto = await get_rubric(rubric_id=rubric.id)
    assert dto["id"] == str(rubric.id)
    assert dto["criteria"] == _CRITERIA
    assert dto["status"] == "active"


async def test_get_rubric_missing_returns_none(bound):
    assert await get_rubric(rubric_id=uuid.uuid4()) is None


async def test_get_rubric_is_cached(monkeypatch):
    rid = uuid.uuid4()
    await get_redis().delete(get_rubric_mod.cache_key(rid))
    calls: list[int] = []

    async def fake_db(**kwargs):
        calls.append(1)

        class R:
            id = rid
            program_id = uuid.uuid4()
            version = 1
            name_ar = None
            name_en = "R"
            criteria = _CRITERIA
            status = "active"

            class _dt:
                @staticmethod
                def isoformat():
                    return "2026-01-01T00:00:00+00:00"

            created_at = _dt()
            updated_at = _dt()

        return R()

    monkeypatch.setattr(get_rubric_mod, "get_rubric_db", fake_db)
    await get_rubric(rubric_id=rid)
    await get_rubric(rubric_id=rid)
    assert len(calls) == 1  # second served from cache


async def test_list_rubrics_never_caches_empty(monkeypatch):
    pid = uuid.uuid4()
    calls: list[int] = []

    async def fake_db(**kwargs):
        calls.append(1)
        return []

    monkeypatch.setattr(list_rubrics_mod, "list_rubrics_db", fake_db)
    await list_rubrics(program_id=pid)
    await list_rubrics(program_id=pid)
    assert len(calls) == 2  # empty not cached


async def test_application_read_and_list(bound):
    program = await _program(bound, f"p-{uuid.uuid4().hex[:8]}")
    cycle = await _cycle(bound, program.id, f"c-{uuid.uuid4().hex[:8]}")
    app = await _application(bound, cycle.id)
    await bound.commit()

    dto = await get_application(application_id=app.id)
    assert dto["applicant_name"] == "Amina"
    assert dto["source_language"] == "en"
    assert dto["status"] == "submitted"

    listed = await list_applications(cycle_id=cycle.id)
    assert any(a["id"] == str(app.id) for a in listed)


async def test_get_application_missing_returns_none(bound):
    assert await get_application(application_id=uuid.uuid4()) is None


async def test_get_application_is_cached(monkeypatch):
    aid = uuid.uuid4()
    await get_redis().delete(get_app_mod.cache_key(aid))
    calls: list[int] = []

    async def fake_db(**kwargs):
        calls.append(1)

        class A:
            id = aid
            cycle_id = uuid.uuid4()
            profile_id = None
            applicant_name = "Amina"
            applicant_email = "a@x.io"
            source_language = "en"
            title = None
            summary = None
            normalized = {}
            original_answers = {}
            status = "submitted"
            ai_total_score = None

            class _dt:
                @staticmethod
                def isoformat():
                    return "2026-01-01T00:00:00+00:00"

            submitted_at = _dt()
            scored_at = None

        return A()

    monkeypatch.setattr(get_app_mod, "get_application_db", fake_db)
    await get_application(application_id=aid)
    await get_application(application_id=aid)
    assert len(calls) == 1
