import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.programs import CohortMember
from nawa_api.utils.logger import get_logger


async def create_cohort_member_db(
    *,
    cohort_id: uuid.UUID,
    profile_id: uuid.UUID,
    role: str = "participant",
    status: str = "active",
    session: AsyncSession | None = None,
) -> CohortMember | None:
    with observe_db(
        operation="write", table="cohort_members", method="create_cohort_member_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = CohortMember(
                    cohort_id=cohort_id, profile_id=profile_id, role=role, status=status
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_cohort_member_db", exc_info=True)
            obs.success = False
            return None
