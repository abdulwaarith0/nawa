import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Application
from nawa_api.utils.logger import get_logger


async def mark_application_normalize_failed_db(
    *, application_id: uuid.UUID, reason: str, session: AsyncSession | None = None
) -> bool:
    """submitted → normalize_failed. The application is NEVER dropped or auto-
    rejected — it stays visible for staff triage with the reason recorded."""
    with observe_db(
        operation="write", table="applications", method="mark_application_normalize_failed_db"
    ) as obs:
        try:
            stmt = (
                update(Application)
                .where(Application.id == application_id)
                .values(status="normalize_failed", normalized={"error": reason})
            )
            async with use_session(session) as s:
                result = await s.execute(stmt)
            obs.success = True
            return (result.rowcount or 0) > 0
        except Exception:
            get_logger().warning(
                "db_error", method="mark_application_normalize_failed_db", exc_info=True
            )
            obs.success = False
            return False
