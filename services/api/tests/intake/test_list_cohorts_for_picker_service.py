import uuid
from datetime import UTC, datetime

import pytest

from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.services.intake.list_cohorts_for_picker import list_cohorts_for_picker
from nawa_api.utils.password import hash_password


async def _manager():
    email = f"{uuid.uuid4().hex[:8]}@x.io"
    return await create_user_db(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("password123"),
        full_name="Manager",
    )


@pytest.mark.asyncio
async def test_list_cohorts_for_picker_scoped_to_cycle():
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P"
    )
    cycle_a = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="A"
    )
    cycle_b = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="B"
    )
    manager = await _manager()
    cohort_a = await create_cohort_db(
        cycle_id=cycle_a.id,
        program_manager_user_id=manager.id,
        name_en="Cohort A",
        starts_at=datetime.now(UTC),
    )
    await create_cohort_db(
        cycle_id=cycle_b.id,
        program_manager_user_id=manager.id,
        name_en="Cohort B",
        starts_at=datetime.now(UTC),
    )

    items = await list_cohorts_for_picker(cycle_id=cycle_a.id)

    assert len(items) == 1
    assert items[0]["id"] == str(cohort_a.id)
    assert items[0]["name_en"] == "Cohort A"


@pytest.mark.asyncio
async def test_list_cohorts_for_picker_empty_cycle_returns_empty_list():
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P"
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C"
    )

    items = await list_cohorts_for_picker(cycle_id=cycle.id)
    assert items == []
