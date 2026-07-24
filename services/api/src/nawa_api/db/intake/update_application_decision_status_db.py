import uuid

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Application
from nawa_api.utils.logger import get_logger


async def update_application_decision_status_db(
    *, application_id: uuid.UUID, status: str, session: AsyncSession | None = None
) -> bool:
    """The only write path allowed to move an application's status PAST
    'scored' (06-intake-copilot.md §6.2) — status is one of
    shortlisted/waitlisted/decided, stamped with decided_at."""
    with observe_db(
        operation="write", table="applications", method="update_application_decision_status_db"
    ) as obs:
        try:
            stmt = (
                update(Application)
                .where(Application.id == application_id)
                .values(status=status, decided_at=func.now())
            )
            async with use_session(session) as s:
                result = await s.execute(stmt)
            obs.success = True
            return (result.rowcount or 0) > 0
        except Exception:
            get_logger().warning(
                "db_error", method="update_application_decision_status_db", exc_info=True
            )
            obs.success = False
            return False
