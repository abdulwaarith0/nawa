import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.programs import Cohort
from nawa_api.utils.logger import get_logger


async def get_cohort_db(
    *, cohort_id: uuid.UUID, session: AsyncSession | None = None
) -> Cohort | None:
    with observe_db(operation="read", table="cohorts", method="get_cohort_db") as obs:
        try:
            async with use_session(session) as s:
                row = (
                    await s.execute(select(Cohort).where(Cohort.id == cohort_id))
                ).scalar_one_or_none()
            obs.success = row is not None
            return row
        except Exception:
            get_logger().warning("db_error", method="get_cohort_db", exc_info=True)
            obs.success = False
            return None
