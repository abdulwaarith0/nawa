"""Fire-and-forget audit writer. Never blocks, never raises, swallows all errors.
Globally toggleable via site_config.audit_enabled."""

import json
import uuid

from nawa_api.db.audit.create_audit_log_db import create_audit_log_db
from nawa_api.services.site_config.get_site_config import get_flag
from nawa_api.utils.logger import get_logger


def _json_safe(value: dict) -> dict:
    """Route bodies are routinely `SomeInput.model_dump()` — the plain (non
    `mode="json"`) form, which leaves UUID/datetime/Decimal fields as live
    Python objects. Postgres's JSONB write chokes on those with a bare
    TypeError, which create_audit_log_db's own except-and-log-only convention
    then swallows — silently dropping the ENTIRE audit row, not just the
    unserializable field. Round-tripping through json.dumps(default=str)
    once here makes every caller's body JSON-safe without each of them
    needing to remember `mode="json"`."""
    return json.loads(json.dumps(value, default=str))


async def create_audit_log(
    *,
    action: str,
    target_type: str,
    actor_id: uuid.UUID | None = None,
    target_id: uuid.UUID | None = None,
    status_code: int | None = None,
    duration_ms: int | None = None,
    request_id: str | None = None,
    ip: str | None = None,
    body: dict | None = None,
) -> None:
    try:
        if not await get_flag("audit_enabled", True):
            return
        metadata = {}
        if request_id is not None:
            metadata["request_id"] = request_id
        if body is not None:
            metadata["body"] = _json_safe(body)
        await create_audit_log_db(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            status_code=status_code,
            duration_ms=duration_ms,
            ip=ip,
            metadata=metadata,
        )
    except Exception:
        get_logger().warning("audit_write_failed", action=action)
