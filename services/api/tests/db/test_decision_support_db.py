import uuid
from datetime import UTC, datetime

import pytest

from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
from nawa_api.db.cohorts.get_cohort_db import get_cohort_db
from nawa_api.db.cohorts.upsert_cohort_member_db import upsert_cohort_member_db
from nawa_api.db.intake.count_higher_scoring_applications_db import (
    count_higher_scoring_applications_db,
)
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.update_application_decision_status_db import (
    update_application_decision_status_db,
)
from nawa_api.db.intake.update_application_profile_link_db import (
    update_application_profile_link_db,
)
from nawa_api.db.intake.update_application_scoring_db import update_application_scoring_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.profiles.get_founder_profile_by_user_id_db import (
    get_founder_profile_by_user_id_db,
)
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.programs.get_program_db import get_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.models.programs import CohortMember


@pytest.mark.asyncio
async def test_get_program_db_round_trips(db_session):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=db_session
    )
    fetched = await get_program_db(program_id=program.id, session=db_session)
    assert fetched is not None
    assert fetched.slug == program.slug


@pytest.mark.asyncio
async def test_get_program_db_missing_returns_none(db_session):
    assert await get_program_db(program_id=uuid.uuid4(), session=db_session) is None


@pytest.mark.asyncio
async def test_get_cohort_db_round_trips(db_session):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=db_session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=db_session
    )
    manager = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"m{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="Manager",
        session=db_session,
    )
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=manager.id,
        starts_at=datetime.now(UTC),
        name_en="Cohort",
        session=db_session,
    )
    fetched = await get_cohort_db(cohort_id=cohort.id, session=db_session)
    assert fetched is not None
    assert fetched.cycle_id == cycle.id


@pytest.mark.asyncio
async def test_get_cohort_db_missing_returns_none(db_session):
    assert await get_cohort_db(cohort_id=uuid.uuid4(), session=db_session) is None


@pytest.mark.asyncio
async def test_upsert_cohort_member_db_is_idempotent(db_session):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=db_session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=db_session
    )
    manager = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"m{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="Manager",
        session=db_session,
    )
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=manager.id,
        starts_at=datetime.now(UTC),
        name_en="Cohort",
        session=db_session,
    )
    founder_user = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"f{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="Founder",
        session=db_session,
    )
    profile = await create_founder_profile_db(
        user_id=founder_user.id,
        handle=f"h-{uuid.uuid4().hex[:8]}",
        display_name_en="Founder",
        session=db_session,
    )

    ok1 = await upsert_cohort_member_db(
        cohort_id=cohort.id, profile_id=profile.id, session=db_session
    )
    ok2 = await upsert_cohort_member_db(
        cohort_id=cohort.id, profile_id=profile.id, session=db_session
    )
    assert ok1 is True
    assert ok2 is True

    from sqlalchemy import select

    rows = (
        await db_session.execute(
            select(CohortMember).where(CohortMember.cohort_id == cohort.id)
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_get_founder_profile_by_user_id_db(db_session):
    user = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"u{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="Founder",
        session=db_session,
    )
    assert await get_founder_profile_by_user_id_db(user_id=user.id, session=db_session) is None

    profile = await create_founder_profile_db(
        user_id=user.id,
        handle=f"h-{uuid.uuid4().hex[:8]}",
        display_name_en="Founder",
        session=db_session,
    )
    fetched = await get_founder_profile_by_user_id_db(user_id=user.id, session=db_session)
    assert fetched is not None
    assert fetched.id == profile.id


@pytest.mark.asyncio
async def test_count_higher_scoring_applications_db(db_session):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=db_session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=db_session
    )
    for score in (10.0, 50.0, 90.0):
        app = await create_application_db(
            cycle_id=cycle.id,
            applicant_name="A",
            applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
            source_language="en",
            original_answers={"idea": "x"},
            session=db_session,
        )
        await update_application_scoring_db(
            application_id=app.id, total_score=score, session=db_session
        )

    assert (
        await count_higher_scoring_applications_db(
            cycle_id=cycle.id, total_score=50.0, session=db_session
        )
        == 1
    )
    assert (
        await count_higher_scoring_applications_db(
            cycle_id=cycle.id, total_score=90.0, session=db_session
        )
        == 0
    )
    assert (
        await count_higher_scoring_applications_db(
            cycle_id=cycle.id, total_score=5.0, session=db_session
        )
        == 3
    )


@pytest.mark.asyncio
async def test_update_application_profile_link_db(db_session):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=db_session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=db_session
    )
    app = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="A",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "x"},
        session=db_session,
    )
    user = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"u{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="Founder",
        session=db_session,
    )
    profile = await create_founder_profile_db(
        user_id=user.id,
        handle=f"h-{uuid.uuid4().hex[:8]}",
        display_name_en="Founder",
        session=db_session,
    )

    updated = await update_application_profile_link_db(
        application_id=app.id, profile_id=profile.id, session=db_session
    )
    assert updated is True

    from sqlalchemy import select

    from nawa_api.models.intake import Application

    stmt = (
        select(Application).where(Application.id == app.id).execution_options(
            populate_existing=True
        )
    )
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.profile_id == profile.id


@pytest.mark.asyncio
async def test_update_application_decision_status_db(db_session):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=db_session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=db_session
    )
    app = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="A",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "x"},
        session=db_session,
    )
    updated = await update_application_decision_status_db(
        application_id=app.id, status="shortlisted", session=db_session
    )
    assert updated is True

    from sqlalchemy import select

    from nawa_api.models.intake import Application

    stmt = (
        select(Application)
        .where(Application.id == app.id)
        .execution_options(populate_existing=True)
    )
    fresh = (await db_session.execute(stmt)).scalar_one()
    assert fresh.status == "shortlisted"
    assert fresh.decided_at is not None
