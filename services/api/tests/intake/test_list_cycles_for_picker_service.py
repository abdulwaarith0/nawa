import uuid

import pytest

from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.services.intake.list_cycles_for_picker import list_cycles_for_picker


@pytest.mark.asyncio
async def test_list_cycles_for_picker_includes_program_name():
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="Rocket Fund"
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="Cycle 1", status="active"
    )

    items = await list_cycles_for_picker()

    match = next(item for item in items if item["id"] == str(cycle.id))
    assert match["program_name_en"] == "Rocket Fund"
    assert match["name_en"] == "Cycle 1"
    assert match["status"] == "active"


@pytest.mark.asyncio
async def test_list_cycles_for_picker_filters_by_status():
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P"
    )
    draft_cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="Draft", status="draft"
    )
    active_cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="Active", status="active"
    )

    items = await list_cycles_for_picker(status="active")
    ids = {item["id"] for item in items}

    assert str(active_cycle.id) in ids
    assert str(draft_cycle.id) not in ids


@pytest.mark.asyncio
async def test_list_cycles_for_picker_reuses_program_lookup_across_cycles():
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="Shared"
    )
    c1 = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C1"
    )
    c2 = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C2"
    )

    items = await list_cycles_for_picker()
    ours = {c1.id, c2.id}
    matched = [item for item in items if uuid.UUID(item["id"]) in ours]

    assert len(matched) == 2
    assert all(item["program_name_en"] == "Shared" for item in matched)
