import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import MilestoneProgress
from nawa_api.utils.logger import get_logger


async def create_milestone_progress_db(
    *,
    milestone_id: uuid.UUID,
    cohort_member_id: uuid.UUID,
    founder_profile_id: uuid.UUID,
    status: str = "not_started",
    note_ar: str | None = None,
    note_en: str | None = None,
    session: AsyncSession | None = None,
) -> MilestoneProgress | None:
    with observe_db(
        operation="write", table="milestone_progress", method="create_milestone_progress_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = MilestoneProgress(
                    milestone_id=milestone_id,
                    cohort_member_id=cohort_member_id,
                    founder_profile_id=founder_profile_id,
                    status=status,
                    note_ar=note_ar,
                    note_en=note_en,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_milestone_progress_db", exc_info=True)
            obs.success = False
            return None
