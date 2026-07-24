"""Cached dedup-match read (06-intake-copilot.md §4).

Key services:intake:list_dedup_matches:<param-hash>, TTL 300s. Invalidated by
the dedup job's inserts (jobs/dedup_scan.py) and by resolution writes (the
dedup-match PATCH route, deferred alongside decisions) via the
services:intake:list_dedup_matches:* glob. Used both for the shortlist row's
"possible prior submission" chip and the scorecard view's side-by-side.
"""

from __future__ import annotations

import json
import uuid
from hashlib import sha256

from pydantic import BaseModel

from nawa_api.db.intake.list_dedup_matches_db import list_dedup_matches_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key

CACHE_TTL_SECONDS = 300
_KEY_PREFIX = "services:intake:list_dedup_matches"


class _DedupMatchList(BaseModel):
    items: list[dict]


def cache_key(application_id: uuid.UUID) -> str:
    raw = json.dumps({"application_id": str(application_id)}, sort_keys=True)
    return f"{_KEY_PREFIX}:{sha256(raw.encode()).hexdigest()[:24]}"


def _dto(row) -> dict:
    return {
        "id": str(row.id),
        "application_id": str(row.application_id),
        "matched_application_id": str(row.matched_application_id),
        "similarity": row.similarity,
        "status": row.status,
        "reviewed_by": str(row.reviewed_by) if row.reviewed_by else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "created_at": row.created_at.isoformat(),
    }


async def list_dedup_matches(*, application_id: uuid.UUID) -> list[dict]:
    key = cache_key(application_id)
    cached = await redis_retrieve_key(key, _DedupMatchList)
    if cached is not None:
        return cached.items
    rows = await list_dedup_matches_db(application_id=application_id)
    items = [_dto(r) for r in rows]
    if items:  # never cache empty
        await redis_update_key(key, _DedupMatchList(items=items), CACHE_TTL_SECONDS)
    return items
