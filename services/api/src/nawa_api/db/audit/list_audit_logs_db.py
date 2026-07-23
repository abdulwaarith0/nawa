import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import clamp_pagination, use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import AuditLog
from nawa_api.utils.logger import get_logger


async def list_audit_logs_db(
    *,
    actor_id: uuid.UUID | None = None,
    action: str | None = None,
    target_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int | None = None,
    offset: int | None = None,
    session: AsyncSession | None = None,
) -> list[AuditLog]:
    clamped_limit, clamped_offset = clamp_pagination(limit=limit, offset=offset)
    with observe_db(operation="read", table="audit_logs", method="list_audit_logs_db") as obs:
        try:
            stmt = select(AuditLog)
            if actor_id is not None:
                stmt = stmt.where(AuditLog.actor_id == actor_id)
            if action is not None:
                stmt = stmt.where(AuditLog.action == action)
            if target_type is not None:
                stmt = stmt.where(AuditLog.target_type == target_type)
            if date_from is not None:
                stmt = stmt.where(AuditLog.created_at >= date_from)
            if date_to is not None:
                stmt = stmt.where(AuditLog.created_at <= date_to)
            stmt = (
                stmt.order_by(AuditLog.created_at.desc())
                .limit(clamped_limit)
                .offset(clamped_offset)
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_audit_logs_db", exc_info=True)
            obs.success = False
            return []
