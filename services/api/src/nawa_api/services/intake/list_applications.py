"""Cached application listing per cycle (06-intake-copilot.md §2).

Key services:intake:list_applications:<param-hash>, TTL 300s. Never caches empty.
"""

from __future__ import annotations

import json
import uuid
from hashlib import sha256

from pydantic import BaseModel

from nawa_api.db.intake.list_applications_db import list_applications_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key
from nawa_api.services.intake._dto import application_dto

CACHE_TTL_SECONDS = 300
_KEY_PREFIX = "services:intake:list_applications"


class _ApplicationList(BaseModel):
    items: list[dict]


def cache_key(cycle_id: uuid.UUID, status: str | None, limit: int) -> str:
    raw = json.dumps(
        {"cycle_id": str(cycle_id), "status": status or "*", "limit": limit}, sort_keys=True
    )
    return f"{_KEY_PREFIX}:{sha256(raw.encode()).hexdigest()[:24]}"


async def list_applications(
    *, cycle_id: uuid.UUID, status: str | None = None, limit: int = 100
) -> list[dict]:
    key = cache_key(cycle_id, status, limit)
    cached = await redis_retrieve_key(key, _ApplicationList)
    if cached is not None:
        return cached.items
    rows = await list_applications_db(cycle_id=cycle_id, status=status, limit=limit)
    items = [application_dto(r) for r in rows]
    if items:  # never cache empty
        await redis_update_key(key, _ApplicationList(items=items), CACHE_TTL_SECONDS)
    return items
