"""Patch an instantiated (cohort-scoped) milestone's dates/titles
(07-journey-copilot.md §2.1/§2.3). Refuses to touch a template row via this
path — 404, never a scope mix-up.

Invalidates the same four cohort-scoped globs as instantiation.
"""

from __future__ import annotations

import uuid

from nawa_api.contracts.errors import ERR_INVALID_FIELDS, ERR_NOT_FOUND
from nawa_api.db.journey.get_milestone_db import get_milestone_db
from nawa_api.db.journey.update_milestone_db import update_milestone_db
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys
from nawa_api.utils.publish_event import publish_event

_INVALIDATION_GLOBS = (
    "services:journey:list_cohort_milestones:*",
    "services:journey:get_cohort_board:*",
    "services:journey:get_member_timeline:*",
    "services:journey:list_at_risk:*",
)


async def update_cohort_milestone(*, milestone_id: uuid.UUID, patch: dict) -> dict:
    row = await get_milestone_db(milestone_id=milestone_id)
    if row is None or row.scope != "cohort":
        raise ERR_NOT_FOUND
    ok = await update_milestone_db(milestone_id=milestone_id, patch=patch)
    if not ok:
        raise ERR_INVALID_FIELDS
    await invalidate_cache_keys(*_INVALIDATION_GLOBS)
    await publish_event(
        f"events:journey:{row.cohort_id}",
        {
            "type": "journey.milestones.instantiated",
            "cohort_id": str(row.cohort_id),
            "milestone_id": str(milestone_id),
        },
    )
    updated = await get_milestone_db(milestone_id=milestone_id)
    return {
        "id": str(updated.id),
        "title_ar": updated.title_ar,
        "title_en": updated.title_en,
        "description_ar": updated.description_ar,
        "description_en": updated.description_en,
        "due_date": updated.due_date.isoformat() if updated.due_date else None,
        "evidence_required": updated.evidence_required,
    }
