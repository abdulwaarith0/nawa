"""Cycle picker for the intake console (06-intake-copilot.md §6.3).

Lists program cycles alongside their program's display name so the upload
view can offer a cycle picker without a second round-trip per row. Not
cached: this is low-traffic, low-volatility config-shaped data compared to
the shortlist read it feeds into.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from nawa_api.db.programs.get_program_db import get_program_db
from nawa_api.db.programs.list_program_cycles_db import list_program_cycles_db


class CyclePickerItem(BaseModel):
    id: uuid.UUID
    program_id: uuid.UUID
    program_name_ar: str | None
    program_name_en: str | None
    name_ar: str | None
    name_en: str | None
    status: str
    opens_at: str | None
    closes_at: str | None


async def list_cycles_for_picker(*, status: str | None = None) -> list[dict]:
    cycles = await list_program_cycles_db(status=status, limit=100)
    programs: dict[uuid.UUID, object] = {}
    items: list[CyclePickerItem] = []
    for cycle in cycles:
        if cycle.program_id not in programs:
            programs[cycle.program_id] = await get_program_db(program_id=cycle.program_id)
        program = programs[cycle.program_id]
        items.append(
            CyclePickerItem(
                id=cycle.id,
                program_id=cycle.program_id,
                program_name_ar=program.name_ar if program else None,
                program_name_en=program.name_en if program else None,
                name_ar=cycle.name_ar,
                name_en=cycle.name_en,
                status=cycle.status,
                opens_at=cycle.opens_at.isoformat() if cycle.opens_at else None,
                closes_at=cycle.closes_at.isoformat() if cycle.closes_at else None,
            )
        )
    return [item.model_dump(mode="json") for item in items]
