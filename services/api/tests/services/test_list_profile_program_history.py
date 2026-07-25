import uuid

import pytest_asyncio

from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
from nawa_api.db.cohorts.create_cohort_member_db import create_cohort_member_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.runtime.redis import get_redis
from nawa_api.services.profiles import list_profile_program_history as history_mod
from nawa_api.services.profiles.list_profile_program_history import (
    cache_key,
    list_profile_program_history,
)


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _profile_in_cohort(session, *, program_name="P"):
    user = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"u{uuid.uuid4().hex[:8]}",
        password_hash="h",
        full_name="F",
        session=session,
    )
    profile = await create_founder_profile_db(
        user_id=user.id, handle=f"h-{uuid.uuid4().hex[:8]}", display_name_en="F", session=session
    )
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="accelerator", name_en=program_name, session=session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=session
    )
    manager = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"m{uuid.uuid4().hex[:8]}",
        password_hash="h",
        full_name="M",
        session=session,
    )
    from datetime import UTC, datetime

    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=manager.id,
        starts_at=datetime(2026, 1, 1, tzinfo=UTC),
        name_en="Cohort",
        session=session,
    )
    await create_cohort_member_db(cohort_id=cohort.id, profile_id=profile.id, session=session)
    return profile, program, cohort


async def test_empty_history_is_not_cached(bound):
    profile = await create_founder_profile_db(
        user_id=(
            await create_user_db(
                email=f"{uuid.uuid4().hex[:8]}@example.com",
                username=f"u{uuid.uuid4().hex[:8]}",
                password_hash="h",
                full_name="F",
                session=bound,
            )
        ).id,
        handle=f"h-{uuid.uuid4().hex[:8]}",
        display_name_en="F",
        session=bound,
    )
    await bound.commit()

    assert await list_profile_program_history(profile_id=profile.id) == []
    assert await get_redis().get(cache_key(profile_id=profile.id)) is None


async def test_returns_program_and_cohort_shape(bound):
    profile, program, cohort = await _profile_in_cohort(bound, program_name="Innovation Fellowship")
    await bound.commit()

    items = await list_profile_program_history(profile_id=profile.id)
    assert len(items) == 1
    assert items[0]["cohort_id"] == str(cohort.id)
    assert items[0]["program_name_en"] == "Innovation Fellowship"
    assert items[0]["role"] == "participant"
    assert items[0]["status"] == "active"


async def test_result_is_cached_until_invalidated(bound, monkeypatch):
    profile, _program, _cohort = await _profile_in_cohort(bound)
    await bound.commit()

    first = await list_profile_program_history(profile_id=profile.id)
    calls = {"n": 0}
    real = history_mod.list_profile_program_history_db

    async def counting(*args, **kwargs):
        calls["n"] += 1
        return await real(*args, **kwargs)

    monkeypatch.setattr(history_mod, "list_profile_program_history_db", counting)
    second = await list_profile_program_history(profile_id=profile.id)
    assert second == first
    assert calls["n"] == 0
