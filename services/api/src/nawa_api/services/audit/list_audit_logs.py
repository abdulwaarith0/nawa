"""Cached audit-log listing (TTL 30 s, never cache empty).

Deliberate exception (documented): create_audit_log fires NO invalidation
globs — the stream is append-only, 30 s staleness is acceptable, and a
fire-and-forget write must never pay for a SCAN.
"""

import uuid

from pydantic import BaseModel

from nawa_api.db.audit.list_audit_logs_db import list_audit_logs_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key

CACHE_TTL_SECONDS = 30


class _AuditList(BaseModel):
    items: list[dict]


def _dto(row) -> dict:
    return {
        "id": str(row.id),
        "actor_id": str(row.actor_id) if row.actor_id else None,
        "actor_type": row.actor_type,
        "action": row.action,
        "target_type": row.target_type,
        "target_id": str(row.target_id) if row.target_id else None,
        "status_code": row.status_code,
        "duration_ms": row.duration_ms,
        "metadata": row.audit_metadata,
        "created_at": row.created_at.isoformat(),
    }


def get_query_key(
    *, actor: str | None, action: str | None, target_type: str | None, limit: int
) -> str:
    return (
        "services:audit:list_audit_logs:"
        f"{actor or '*'}:{action or '*'}:{target_type or '*'}:{limit}"
    )


async def list_audit_logs(
    *,
    actor: str | None = None,
    action: str | None = None,
    target_type: str | None = None,
    limit: int = 100,
) -> list[dict]:
    key = get_query_key(actor=actor, action=action, target_type=target_type, limit=limit)
    cached = await redis_retrieve_key(key, _AuditList)
    if cached is not None:
        return cached.items
    actor_id = uuid.UUID(actor) if actor else None
    rows = await list_audit_logs_db(
        actor_id=actor_id, action=action, target_type=target_type, limit=limit
    )
    items = [_dto(r) for r in rows]
    if items:  # never cache empty
        await redis_update_key(key, _AuditList(items=items), CACHE_TTL_SECONDS)
    return items
