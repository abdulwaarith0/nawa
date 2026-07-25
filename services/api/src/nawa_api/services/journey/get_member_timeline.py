"""Cached founder-facing timeline (07-journey-copilot.md §2.1/§2.3): every
instantiated cohort milestone in sequence order, paired with this member's
own progress row (left-join shape, assembled here since the db layer
returns two flat sets).

Key services:journey:get_member_timeline:<founder_profile_id>:<cohort_id>,
TTL 300s. Invalidated by progress writes for that member.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel

from nawa_api.db.journey.get_member_timeline_db import get_member_timeline_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key

CACHE_TTL_SECONDS = 300
_NOT_OVERDUE_STATUSES = frozenset({"done", "waived"})


class _CachedTimeline(BaseModel):
    items: list[dict]


def cache_key(*, founder_profile_id: uuid.UUID, cohort_id: uuid.UUID) -> str:
    return f"services:journey:get_member_timeline:{founder_profile_id}:{cohort_id}"


async def get_member_timeline(*, founder_profile_id: uuid.UUID, cohort_id: uuid.UUID) -> list[dict]:
    key = cache_key(founder_profile_id=founder_profile_id, cohort_id=cohort_id)
    cached = await redis_retrieve_key(key, _CachedTimeline)
    if cached is not None:
        return cached.items

    raw = await get_member_timeline_db(founder_profile_id=founder_profile_id, cohort_id=cohort_id)
    progress_by_milestone = {p.milestone_id: p for p in raw["progress"]}
    as_of = datetime.now(UTC).date()

    items = []
    for milestone in sorted(raw["milestones"], key=lambda m: m.sequence):
        progress = progress_by_milestone.get(milestone.id)
        status = progress.status if progress else "not_started"
        overdue = (
            milestone.due_date is not None
            and milestone.due_date < as_of
            and status not in _NOT_OVERDUE_STATUSES
        )
        items.append(
            {
                "milestone_id": str(milestone.id),
                "sequence": milestone.sequence,
                "title_ar": milestone.title_ar,
                "title_en": milestone.title_en,
                "description_ar": milestone.description_ar,
                "description_en": milestone.description_en,
                "due_date": milestone.due_date.isoformat() if milestone.due_date else None,
                "evidence_required": milestone.evidence_required,
                "progress_id": str(progress.id) if progress else None,
                "status": status,
                "note_ar": progress.note_ar if progress else None,
                "note_en": progress.note_en if progress else None,
                "evidence_links": progress.evidence_links if progress else [],
                "overdue": overdue,
            }
        )

    if items:  # never cache empty
        await redis_update_key(key, _CachedTimeline(items=items), CACHE_TTL_SECONDS)
    return items
