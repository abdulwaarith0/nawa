import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import clamp_pagination, use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.programs import Cohort
from nawa_api.utils.logger import get_logger


async def list_cohorts_db(
    *,
    cycle_id: uuid.UUID | None = None,
    limit: int | None = None,
    offset: int | None = None,
    session: AsyncSession | None = None,
) -> list[Cohort]:
    clamped_limit, clamped_offset = clamp_pagination(limit=limit, offset=offset)
    with observe_db(operation="read", table="cohorts", method="list_cohorts_db") as obs:
        try:
            stmt = select(Cohort)
            if cycle_id is not None:
                stmt = stmt.where(Cohort.cycle_id == cycle_id)
            stmt = (
                stmt.order_by(Cohort.starts_at.desc()).limit(clamped_limit).offset(clamped_offset)
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_cohorts_db", exc_info=True)
            obs.success = False
            return []
