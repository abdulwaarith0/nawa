import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import Milestone
from nawa_api.utils.logger import get_logger


async def delete_milestone_db(
    *, milestone_id: uuid.UUID, session: AsyncSession | None = None
) -> bool:
    with observe_db(operation="write", table="milestones", method="delete_milestone_db") as obs:
        try:
            stmt = delete(Milestone).where(Milestone.id == milestone_id)
            async with use_session(session) as s:
                result = await s.execute(stmt)
            obs.success = True
            return (result.rowcount or 0) > 0
        except Exception:
            get_logger().warning("db_error", method="delete_milestone_db", exc_info=True)
            obs.success = False
            return False
