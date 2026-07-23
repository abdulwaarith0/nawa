"""Cached single-rubric read (06-intake-copilot.md §1).

Key services:intake:get_rubric:<rubric_id>, TTL 600s. Invalidated by rubric
writes (create / new-version / status change).
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from nawa_api.db.intake.get_rubric_db import get_rubric_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key
from nawa_api.services.intake._dto import rubric_dto

CACHE_TTL_SECONDS = 600


class _CachedRubric(BaseModel):
    item: dict


def cache_key(rubric_id: uuid.UUID) -> str:
    return f"services:intake:get_rubric:{rubric_id}"


async def get_rubric(*, rubric_id: uuid.UUID) -> dict | None:
    key = cache_key(rubric_id)
    cached = await redis_retrieve_key(key, _CachedRubric)
    if cached is not None:
        return cached.item
    row = await get_rubric_db(rubric_id=rubric_id)
    if row is None:
        return None
    item = rubric_dto(row)
    await redis_update_key(key, _CachedRubric(item=item), CACHE_TTL_SECONDS)
    return item
