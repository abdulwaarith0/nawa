import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Rubric
from nawa_api.utils.logger import get_logger


async def get_active_rubric_db(
    *, program_id: uuid.UUID, session: AsyncSession | None = None
) -> Rubric | None:
    with observe_db(operation="read", table="rubrics", method="get_active_rubric_db") as obs:
        try:
            stmt = select(Rubric).where(Rubric.program_id == program_id, Rubric.status == "active")
            async with use_session(session) as s:
                row = (await s.execute(stmt)).scalar_one_or_none()
            obs.success = row is not None
            return row
        except Exception:
            get_logger().warning("db_error", method="get_active_rubric_db", exc_info=True)
            obs.success = False
            return None
