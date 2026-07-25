import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import MilestoneProgress
from nawa_api.utils.logger import get_logger


async def get_milestone_progress_db(
    *, progress_id: uuid.UUID, session: AsyncSession | None = None
) -> MilestoneProgress | None:
    with observe_db(
        operation="read", table="milestone_progress", method="get_milestone_progress_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = (
                    await s.execute(
                        select(MilestoneProgress).where(MilestoneProgress.id == progress_id)
                    )
                ).scalar_one_or_none()
            obs.success = row is not None
            return row
        except Exception:
            get_logger().warning("db_error", method="get_milestone_progress_db", exc_info=True)
            obs.success = False
            return None
