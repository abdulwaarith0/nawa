"""Admin read of the ai_calls ledger (05-ai-infrastructure.md §7 / §11).

Cache key services:ai_calls:list_ai_calls:<canonical-param-hash>, TTL 300s. The
only writer is the gateway's fire-and-forget insert, which invalidates the
`services:ai_calls:list_ai_calls:*` glob on every call. Empty results are never
cached (canon).
"""

from __future__ import annotations

import json
import uuid
from hashlib import sha256

from pydantic import BaseModel

from nawa_api.db.ai_calls.list_ai_calls_db import list_ai_calls_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key

CACHE_TTL_SECONDS = 300
_KEY_PREFIX = "services:ai_calls:list_ai_calls"


class _AiCallList(BaseModel):
    items: list[dict]


def get_query_key(
    *, task: str | None, provider: str | None, status: str | None, cycle: str | None, limit: int
) -> str:
    raw = json.dumps(
        {"task": task, "provider": provider, "status": status, "cycle": cycle, "limit": limit},
        sort_keys=True,
    )
    return f"{_KEY_PREFIX}:{sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _dto(row) -> dict:
    return {
        "id": str(row.id),
        "task": row.task,
        "provider": row.provider,
        "model": row.model,
        "tier": row.tier,
        "status": row.status,
        "error_code": row.error_code,
        "tokens_in": row.tokens_in,
        "tokens_out": row.tokens_out,
        "tokens_cached": row.tokens_cached,
        "cost_estimate": str(row.cost_estimate),
        "latency_ms": row.latency_ms,
        "request_id": row.request_id,
        "cycle_id": str(row.cycle_id) if row.cycle_id else None,
        "created_by": str(row.created_by) if row.created_by else None,
        "subject_type": row.subject_type,
        "subject_id": str(row.subject_id) if row.subject_id else None,
        "created_at": row.created_at.isoformat(),
    }


async def list_ai_calls(
    *,
    task: str | None = None,
    provider: str | None = None,
    status: str | None = None,
    cycle: str | None = None,
    limit: int = 100,
) -> list[dict]:
    key = get_query_key(task=task, provider=provider, status=status, cycle=cycle, limit=limit)
    cached = await redis_retrieve_key(key, _AiCallList)
    if cached is not None:
        return cached.items
    cycle_id = uuid.UUID(cycle) if cycle else None
    rows = await list_ai_calls_db(
        task=task, provider=provider, status=status, cycle_id=cycle_id, limit=limit
    )
    items = [_dto(r) for r in rows]
    if items:  # never cache empty
        await redis_update_key(key, _AiCallList(items=items), CACHE_TTL_SECONDS)
    return items
