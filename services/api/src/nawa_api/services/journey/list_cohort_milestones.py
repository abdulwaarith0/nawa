"""Cached instantiated-milestone list for one cohort (07-journey-copilot.md
§2.3). Key services:journey:list_cohort_milestones:<cohort_id>, TTL 600s.
Invalidated by instantiation and cohort-milestone updates.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from nawa_api.db.journey.list_milestones_db import list_milestones_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key

CACHE_TTL_SECONDS = 600


class _CachedList(BaseModel):
    items: list[dict]


def cache_key(*, cohort_id: uuid.UUID) -> str:
    return f"services:journey:list_cohort_milestones:{cohort_id}"


def _dto(row) -> dict:
    return {
        "id": str(row.id),
        "sequence": row.sequence,
        "title_ar": row.title_ar,
        "title_en": row.title_en,
        "description_ar": row.description_ar,
        "description_en": row.description_en,
        "due_date": row.due_date.isoformat() if row.due_date else None,
        "evidence_required": row.evidence_required,
        "template_id": str(row.template_id) if row.template_id else None,
    }


async def list_cohort_milestones(*, cohort_id: uuid.UUID) -> list[dict]:
    key = cache_key(cohort_id=cohort_id)
    cached = await redis_retrieve_key(key, _CachedList)
    if cached is not None:
        return cached.items
    rows = await list_milestones_db(cohort_id=cohort_id, scope="cohort")
    items = [_dto(row) for row in rows]
    if items:  # never cache empty
        await redis_update_key(key, _CachedList(items=items), CACHE_TTL_SECONDS)
    return items
