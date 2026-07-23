import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import MilestoneProgress
from nawa_api.utils.logger import get_logger


async def list_milestone_progress_db(
    *,
    founder_profile_id: uuid.UUID | None = None,
    cohort_member_id: uuid.UUID | None = None,
    session: AsyncSession | None = None,
) -> list[MilestoneProgress]:
    with observe_db(
        operation="read", table="milestone_progress", method="list_milestone_progress_db"
    ) as obs:
        try:
            stmt = select(MilestoneProgress)
            if founder_profile_id is not None:
                stmt = stmt.where(MilestoneProgress.founder_profile_id == founder_profile_id)
            if cohort_member_id is not None:
                stmt = stmt.where(MilestoneProgress.cohort_member_id == cohort_member_id)
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_milestone_progress_db", exc_info=True)
            obs.success = False
            return []
