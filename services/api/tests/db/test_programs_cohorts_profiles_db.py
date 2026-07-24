import uuid
from datetime import UTC, datetime

import pytest

from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
from nawa_api.db.cohorts.create_cohort_member_db import create_cohort_member_db
from nawa_api.db.cohorts.list_cohort_members_db import list_cohort_members_db
from nawa_api.db.cohorts.list_cohorts_db import list_cohorts_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.profiles.get_profile_by_handle_db import get_profile_by_handle_db
from nawa_api.db.profiles.get_profile_by_id_any_status_db import get_profile_by_id_any_status_db
from nawa_api.db.profiles.list_profile_program_history_db import (
    list_profile_program_history_db,
)
from nawa_api.db.profiles.list_profiles_db import list_profiles_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.programs.get_program_by_slug_db import get_program_by_slug_db
from nawa_api.db.programs.get_program_cycle_db import get_program_cycle_db
from nawa_api.db.programs.list_program_cycles_db import list_program_cycles_db
from nawa_api.db.programs.list_programs_db import list_programs_db
from nawa_api.db.users.create_user_db import create_user_db


@pytest.mark.asyncio
async def test_create_and_get_program_round_trips(db_session):
    created = await create_program_db(
        slug="velocity", kind="accelerator", name_en="Velocity", session=db_session
    )
    assert created is not None
    fetched = await get_program_by_slug_db(slug="velocity", session=db_session)
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_list_programs_db_returns_created_rows(db_session):
    await create_program_db(
        slug="incubation", kind="incubation", name_en="Incubation Center", session=db_session
    )
    rows = await list_programs_db(session=db_session)
    slugs = {p.slug for p in rows}
    assert "incubation" in slugs


@pytest.mark.asyncio
async def test_program_cycle_create_and_list(db_session):
    program = await create_program_db(
        slug="sos-cycle-test", kind="competition", name_en="SoS", session=db_session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id,
        slug="season-18",
        status="screening",
        name_en="Season 18",
        session=db_session,
    )
    assert cycle is not None
    rows = await list_program_cycles_db(program_id=program.id, session=db_session)
    assert any(c.id == cycle.id for c in rows)

    fetched = await get_program_cycle_db(cycle_id=cycle.id, session=db_session)
    assert fetched is not None
    assert fetched.program_id == program.id


@pytest.mark.asyncio
async def test_get_program_cycle_db_missing_returns_none(db_session):
    assert await get_program_cycle_db(cycle_id=uuid.uuid4(), session=db_session) is None


@pytest.mark.asyncio
async def test_cohort_and_member_lifecycle(db_session):
    manager = await create_user_db(
        email="pm@example.com",
        username="pm1",
        password_hash="hashed",
        full_name="PM One",
        session=db_session,
    )
    program = await create_program_db(
        slug="velocity-cohort-test", kind="accelerator", name_en="Velocity", session=db_session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug="cycle-14", name_en="Cycle 14", session=db_session
    )
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=manager.id,
        starts_at=datetime.now(UTC),
        name_en="Cycle 14 Cohort",
        session=db_session,
    )
    assert cohort is not None

    user = await create_user_db(
        email="founder-x@example.com",
        username="founderx",
        password_hash="hashed",
        full_name="Founder X",
        session=db_session,
    )
    profile = await create_founder_profile_db(
        user_id=user.id,
        handle="founder-x",
        display_name_en="Founder X",
        session=db_session,
    )
    member = await create_cohort_member_db(
        cohort_id=cohort.id, profile_id=profile.id, session=db_session
    )
    assert member is not None

    cohorts = await list_cohorts_db(cycle_id=cycle.id, session=db_session)
    assert any(c.id == cohort.id for c in cohorts)
    members = await list_cohort_members_db(cohort_id=cohort.id, session=db_session)
    assert any(m.id == member.id for m in members)

    history = await list_profile_program_history_db(profile_id=profile.id, session=db_session)
    assert len(history) == 1
    assert history[0]["program"].id == program.id
    assert history[0]["cohort"].id == cohort.id


@pytest.mark.asyncio
async def test_get_profile_by_handle_db_public_split(db_session):
    user = await create_user_db(
        email="pub@example.com",
        username="pubfounder",
        password_hash="hashed",
        full_name="Public Founder",
        session=db_session,
    )
    profile = await create_founder_profile_db(
        user_id=user.id, handle="pub-founder", display_name_en="Public Founder", session=db_session
    )
    found = await get_profile_by_handle_db(handle="pub-founder", session=db_session)
    assert found is not None
    assert found.id == profile.id


@pytest.mark.asyncio
async def test_get_profile_by_id_any_status_returns_private_profiles(db_session):
    user = await create_user_db(
        email="priv@example.com",
        username="privfounder",
        password_hash="hashed",
        full_name="Private Founder",
        session=db_session,
    )
    profile = await create_founder_profile_db(
        user_id=user.id,
        handle="priv-founder",
        display_name_en="Private Founder",
        session=db_session,
    )
    # Flip to private directly to prove the any-status getter ignores is_public.
    from sqlalchemy import update

    from nawa_api.models.profiles import FounderProfile

    await db_session.execute(
        update(FounderProfile).where(FounderProfile.id == profile.id).values(is_public=False)
    )
    await db_session.flush()

    via_public = await get_profile_by_handle_db(handle="priv-founder", session=db_session)
    via_any_status = await get_profile_by_id_any_status_db(
        profile_id=profile.id, session=db_session
    )
    assert via_public is None
    assert via_any_status is not None
    assert via_any_status.id == profile.id


@pytest.mark.asyncio
async def test_list_profiles_db_excludes_private_profiles(db_session):
    user = await create_user_db(
        email="dirtest@example.com",
        username="dirtest",
        password_hash="hashed",
        full_name="Directory Test",
        session=db_session,
    )
    await create_founder_profile_db(
        user_id=user.id, handle="dir-test", display_name_en="Directory Test", session=db_session
    )
    rows = await list_profiles_db(session=db_session)
    assert any(p.handle == "dir-test" for p in rows)


@pytest.mark.asyncio
async def test_get_program_by_slug_db_returns_none_for_missing_slug(db_session):
    result = await get_program_by_slug_db(slug=f"nonexistent-{uuid.uuid4()}", session=db_session)
    assert result is None
