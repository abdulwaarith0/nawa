import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Rubric
from nawa_api.utils.logger import get_logger


async def create_rubric_db(
    *,
    program_id: uuid.UUID,
    version: int,
    criteria: list,
    name_ar: str | None = None,
    name_en: str | None = None,
    status: str = "draft",
    session: AsyncSession | None = None,
) -> Rubric | None:
    with observe_db(operation="write", table="rubrics", method="create_rubric_db") as obs:
        try:
            async with use_session(session) as s:
                row = Rubric(
                    program_id=program_id,
                    version=version,
                    criteria=criteria,
                    name_ar=name_ar,
                    name_en=name_en,
                    status=status,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_rubric_db", exc_info=True)
            obs.success = False
            return None
