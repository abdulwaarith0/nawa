"""Cached single-application read (06-intake-copilot.md §2).

Key services:intake:get_application:<id>, TTL 300s. Invalidated by create /
normalize / document-attach writes.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from nawa_api.db.intake.get_application_db import get_application_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key
from nawa_api.services.intake._dto import application_dto

CACHE_TTL_SECONDS = 300


class _CachedApplication(BaseModel):
    item: dict


def cache_key(application_id: uuid.UUID) -> str:
    return f"services:intake:get_application:{application_id}"


async def get_application(*, application_id: uuid.UUID) -> dict | None:
    key = cache_key(application_id)
    cached = await redis_retrieve_key(key, _CachedApplication)
    if cached is not None:
        return cached.item
    row = await get_application_db(application_id=application_id)
    if row is None:
        return None
    item = application_dto(row)
    await redis_update_key(key, _CachedApplication(item=item), CACHE_TTL_SECONDS)
    return item
