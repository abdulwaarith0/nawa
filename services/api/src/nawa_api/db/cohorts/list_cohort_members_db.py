import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import clamp_pagination, use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.programs import CohortMember
from nawa_api.utils.logger import get_logger


async def list_cohort_members_db(
    *,
    cohort_id: uuid.UUID,
    limit: int | None = None,
    offset: int | None = None,
    session: AsyncSession | None = None,
) -> list[CohortMember]:
    clamped_limit, clamped_offset = clamp_pagination(limit=limit, offset=offset)
    with observe_db(
        operation="read", table="cohort_members", method="list_cohort_members_db"
    ) as obs:
        try:
            stmt = (
                select(CohortMember)
                .where(CohortMember.cohort_id == cohort_id)
                .order_by(CohortMember.joined_at.desc())
                .limit(clamped_limit)
                .offset(clamped_offset)
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_cohort_members_db", exc_info=True)
            obs.success = False
            return []
