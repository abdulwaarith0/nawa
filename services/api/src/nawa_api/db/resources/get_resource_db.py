import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import Resource
from nawa_api.utils.logger import get_logger


async def get_resource_db(
    *, resource_id: uuid.UUID, session: AsyncSession | None = None
) -> Resource | None:
    with observe_db(operation="read", table="resources", method="get_resource_db") as obs:
        try:
            async with use_session(session) as s:
                row = (
                    await s.execute(select(Resource).where(Resource.id == resource_id))
                ).scalar_one_or_none()
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="get_resource_db", exc_info=True)
            obs.success = False
            return None
