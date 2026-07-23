"""Daily audit-log retention purge (arq cron). Deletes rows past expires_at."""

from nawa_api.db.audit.purge_expired_audit_logs_db import purge_expired_audit_logs_db
from nawa_api.utils.logger import get_logger


async def purge_audit_logs(_ctx: dict | None = None) -> int:
    removed = await purge_expired_audit_logs_db()
    get_logger().info("purge_audit_logs_complete", removed=removed)
    return removed
