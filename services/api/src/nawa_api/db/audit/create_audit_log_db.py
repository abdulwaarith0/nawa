import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import days_ago, use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import AuditLog
from nawa_api.utils.logger import get_logger

_DEFAULT_RETENTION_DAYS = 180


async def create_audit_log_db(
    *,
    action: str,
    target_type: str,
    actor_id: uuid.UUID | None = None,
    actor_type: str = "user",
    target_id: uuid.UUID | None = None,
    status_code: int | None = None,
    duration_ms: int | None = None,
    ip: str | None = None,
    metadata: dict | None = None,
    expires_at: datetime | None = None,
    session: AsyncSession | None = None,
) -> AuditLog | None:
    """Fire-and-forget writer: callers (the @audited decorator) must never let
    an exception here fail the request it's logging."""
    with observe_db(operation="write", table="audit_logs", method="create_audit_log_db") as obs:
        try:
            # days_ago(n) is now() - n days, so a negative n lands in the future.
            resolved_expiry = expires_at or days_ago(-_DEFAULT_RETENTION_DAYS)
            async with use_session(session) as s:
                row = AuditLog(
                    actor_id=actor_id,
                    actor_type=actor_type,
                    action=action,
                    target_type=target_type,
                    target_id=target_id,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    ip=ip,
                    audit_metadata=metadata or {},
                    expires_at=resolved_expiry,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_audit_log_db", exc_info=True)
            obs.success = False
            return None
