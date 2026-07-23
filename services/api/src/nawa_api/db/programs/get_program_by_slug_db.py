from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.programs import Program
from nawa_api.utils.logger import get_logger


async def get_program_by_slug_db(
    *, slug: str, session: AsyncSession | None = None
) -> Program | None:
    with observe_db(operation="read", table="programs", method="get_program_by_slug_db") as obs:
        try:
            async with use_session(session) as s:
                row = (
                    await s.execute(select(Program).where(Program.slug == slug))
                ).scalar_one_or_none()
            obs.success = row is not None
            return row
        except Exception:
            get_logger().warning("db_error", method="get_program_by_slug_db", exc_info=True)
            obs.success = False
            return None
