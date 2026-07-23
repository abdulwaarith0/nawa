from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import AuditLog
from nawa_api.utils.logger import get_logger


async def purge_expired_audit_logs_db(*, session: AsyncSession | None = None) -> int:
    """Delete audit rows whose retention horizon (expires_at) has passed.
    Returns the number of rows removed."""
    with observe_db(
        operation="delete", table="audit_logs", method="purge_expired_audit_logs_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                result = await s.execute(
                    delete(AuditLog).where(AuditLog.expires_at < datetime.now(UTC))
                )
            obs.success = True
            return result.rowcount or 0
        except Exception:
            get_logger().warning("db_error", method="purge_expired_audit_logs_db", exc_info=True)
            obs.success = False
            return 0
