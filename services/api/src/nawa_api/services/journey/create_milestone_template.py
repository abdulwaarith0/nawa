"""Create a milestone template row (07-journey-copilot.md §2.1/§2.3).

Write-only; invalidates services:journey:list_milestone_templates:*.
"""

from __future__ import annotations

import uuid

from nawa_api.contracts.errors import ERR_INVALID_FIELDS
from nawa_api.db.journey.create_milestone_db import create_milestone_db
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys


async def create_milestone_template(
    *,
    program_id: uuid.UUID,
    sequence: int,
    program_cycle_id: uuid.UUID | None = None,
    title_ar: str | None = None,
    title_en: str | None = None,
    description_ar: str | None = None,
    description_en: str | None = None,
    due_offset_days: int | None = None,
    evidence_required: bool = False,
    config: dict | None = None,
) -> dict:
    if not title_ar and not title_en:
        raise ERR_INVALID_FIELDS
    row = await create_milestone_db(
        program_id=program_id,
        program_cycle_id=program_cycle_id,
        scope="template",
        sequence=sequence,
        title_ar=title_ar,
        title_en=title_en,
        description_ar=description_ar,
        description_en=description_en,
        due_offset_days=due_offset_days,
        evidence_required=evidence_required,
        config=config,
    )
    if row is None:
        raise ERR_INVALID_FIELDS
    await invalidate_cache_keys("services:journey:list_milestone_templates:*")
    return {
        "id": str(row.id),
        "program_id": str(row.program_id),
        "program_cycle_id": str(row.program_cycle_id) if row.program_cycle_id else None,
        "sequence": row.sequence,
        "title_ar": row.title_ar,
        "title_en": row.title_en,
        "description_ar": row.description_ar,
        "description_en": row.description_en,
        "due_offset_days": row.due_offset_days,
        "evidence_required": row.evidence_required,
    }
