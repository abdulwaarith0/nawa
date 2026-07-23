"""Minimal real-row factories shared across db-layer tests.

Each factory inserts through the actual db-layer functions (never raw ORM
inserts) so tests double as an integration shakeout of the layer itself.
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db


async def make_user(session: AsyncSession, *, email: str = "u@example.com", username: str = "u"):
    return await create_user_db(
        email=email,
        username=username,
        password_hash="hashed",
        full_name="Test User",
        session=session,
    )


async def make_program(session: AsyncSession, *, slug: str = "sos"):
    return await create_program_db(
        slug=slug,
        name_ar="نجوم العلوم",
        name_en="Innovation Fellowship",
        kind="competition",
        session=session,
    )


async def make_cycle(session: AsyncSession, *, program_id, slug: str = "season-18"):
    return await create_program_cycle_db(
        program_id=program_id,
        slug=slug,
        name_ar="الموسم 18",
        name_en="Season 18",
        status="screening",
        session=session,
    )


async def make_cohort(session: AsyncSession, *, cycle_id, manager_user_id, name_en="Cohort A"):
    return await create_cohort_db(
        cycle_id=cycle_id,
        name_ar="الدفعة أ",
        name_en=name_en,
        program_manager_user_id=manager_user_id,
        starts_at=datetime.now(UTC),
        session=session,
    )


async def make_profile(session: AsyncSession, *, user_id, handle: str = "founder-1"):
    return await create_founder_profile_db(
        user_id=user_id,
        handle=handle,
        display_name_ar="أحمد",
        display_name_en="Ahmed",
        session=session,
    )
