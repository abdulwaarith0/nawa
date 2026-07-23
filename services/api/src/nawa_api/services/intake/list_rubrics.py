"""Cached rubric listing per program (06-intake-copilot.md §1).

Key services:intake:list_rubrics:<param-hash>, TTL 600s. Never caches empty.
"""

from __future__ import annotations

import json
import uuid
from hashlib import sha256

from pydantic import BaseModel

from nawa_api.db.intake.list_rubrics_db import list_rubrics_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key
from nawa_api.services.intake._dto import rubric_dto

CACHE_TTL_SECONDS = 600
_KEY_PREFIX = "services:intake:list_rubrics"


class _RubricList(BaseModel):
    items: list[dict]


def cache_key(program_id: uuid.UUID, status: str | None) -> str:
    raw = json.dumps({"program_id": str(program_id), "status": status or "*"}, sort_keys=True)
    return f"{_KEY_PREFIX}:{sha256(raw.encode()).hexdigest()[:24]}"


async def list_rubrics(*, program_id: uuid.UUID, status: str | None = None) -> list[dict]:
    key = cache_key(program_id, status)
    cached = await redis_retrieve_key(key, _RubricList)
    if cached is not None:
        return cached.items
    rows = await list_rubrics_db(program_id=program_id, status=status)
    items = [rubric_dto(r) for r in rows]
    if items:  # never cache empty
        await redis_update_key(key, _RubricList(items=items), CACHE_TTL_SECONDS)
    return items
