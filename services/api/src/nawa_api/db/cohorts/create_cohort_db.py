import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.programs import Cohort
from nawa_api.utils.logger import get_logger


async def create_cohort_db(
    *,
    cycle_id: uuid.UUID,
    program_manager_user_id: uuid.UUID,
    starts_at: datetime,
    name_ar: str | None = None,
    name_en: str | None = None,
    ends_at: datetime | None = None,
    session: AsyncSession | None = None,
) -> Cohort | None:
    with observe_db(operation="write", table="cohorts", method="create_cohort_db") as obs:
        try:
            async with use_session(session) as s:
                row = Cohort(
                    cycle_id=cycle_id,
                    program_manager_user_id=program_manager_user_id,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    name_ar=name_ar,
                    name_en=name_en,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_cohort_db", exc_info=True)
            obs.success = False
            return None
