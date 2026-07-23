import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Rubric
from nawa_api.utils.logger import get_logger


async def list_rubrics_db(
    *,
    program_id: uuid.UUID,
    status: str | None = None,
    session: AsyncSession | None = None,
) -> list[Rubric]:
    with observe_db(operation="read", table="rubrics", method="list_rubrics_db") as obs:
        try:
            stmt = select(Rubric).where(Rubric.program_id == program_id)
            if status is not None:
                stmt = stmt.where(Rubric.status == status)
            stmt = stmt.order_by(Rubric.version.desc())
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_rubrics_db", exc_info=True)
            obs.success = False
            return []
