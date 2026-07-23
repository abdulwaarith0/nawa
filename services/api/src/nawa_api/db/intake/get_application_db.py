import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Application
from nawa_api.utils.logger import get_logger


async def get_application_db(
    *, application_id: uuid.UUID, session: AsyncSession | None = None
) -> Application | None:
    with observe_db(operation="read", table="applications", method="get_application_db") as obs:
        try:
            async with use_session(session) as s:
                row = (
                    await s.execute(select(Application).where(Application.id == application_id))
                ).scalar_one_or_none()
            obs.success = row is not None
            return row
        except Exception:
            get_logger().warning("db_error", method="get_application_db", exc_info=True)
            obs.success = False
            return None
