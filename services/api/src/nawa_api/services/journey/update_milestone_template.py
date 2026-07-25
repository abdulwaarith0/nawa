"""Patch a milestone template (07-journey-copilot.md §2.1/§2.3). Refuses to
touch an id that isn't a template row — 404, never silently repurposed.

Invalidates services:journey:list_milestone_templates:*.
"""

from __future__ import annotations

import uuid

from nawa_api.contracts.errors import ERR_INVALID_FIELDS, ERR_NOT_FOUND
from nawa_api.db.journey.get_milestone_db import get_milestone_db
from nawa_api.db.journey.update_milestone_db import update_milestone_db
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys


async def update_milestone_template(*, milestone_id: uuid.UUID, patch: dict) -> dict:
    row = await get_milestone_db(milestone_id=milestone_id)
    if row is None or row.scope != "template":
        raise ERR_NOT_FOUND
    ok = await update_milestone_db(milestone_id=milestone_id, patch=patch)
    if not ok:
        raise ERR_INVALID_FIELDS
    await invalidate_cache_keys("services:journey:list_milestone_templates:*")
    updated = await get_milestone_db(milestone_id=milestone_id)
    return {
        "id": str(updated.id),
        "title_ar": updated.title_ar,
        "title_en": updated.title_en,
        "description_ar": updated.description_ar,
        "description_en": updated.description_en,
        "sequence": updated.sequence,
        "due_offset_days": updated.due_offset_days,
        "evidence_required": updated.evidence_required,
    }
