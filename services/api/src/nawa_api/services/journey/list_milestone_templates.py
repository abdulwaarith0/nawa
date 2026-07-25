"""Cached template list (07-journey-copilot.md §2.3).

Key services:journey:list_milestone_templates:<program_id>:<cycle_id|*>,
TTL 600s. Invalidated by template create/update/delete.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from nawa_api.db.journey.list_milestone_templates_db import list_milestone_templates_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key

CACHE_TTL_SECONDS = 600


class _CachedList(BaseModel):
    items: list[dict]


def cache_key(*, program_id: uuid.UUID, program_cycle_id: uuid.UUID | None) -> str:
    return f"services:journey:list_milestone_templates:{program_id}:{program_cycle_id or '*'}"


def _dto(row) -> dict:
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
        "config": row.config,
    }


async def list_milestone_templates(
    *, program_id: uuid.UUID, program_cycle_id: uuid.UUID | None = None
) -> list[dict]:
    key = cache_key(program_id=program_id, program_cycle_id=program_cycle_id)
    cached = await redis_retrieve_key(key, _CachedList)
    if cached is not None:
        return cached.items
    rows = await list_milestone_templates_db(
        program_id=program_id, program_cycle_id=program_cycle_id
    )
    items = [_dto(row) for row in rows]
    if items:  # never cache empty
        await redis_update_key(key, _CachedList(items=items), CACHE_TTL_SECONDS)
    return items
