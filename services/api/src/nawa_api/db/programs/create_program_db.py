from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.programs import Program
from nawa_api.utils.logger import get_logger


async def create_program_db(
    *,
    slug: str,
    kind: str,
    name_ar: str | None = None,
    name_en: str | None = None,
    description_ar: str | None = None,
    description_en: str | None = None,
    config: dict | None = None,
    session: AsyncSession | None = None,
) -> Program | None:
    with observe_db(operation="write", table="programs", method="create_program_db") as obs:
        try:
            async with use_session(session) as s:
                row = Program(
                    slug=slug,
                    kind=kind,
                    name_ar=name_ar,
                    name_en=name_en,
                    description_ar=description_ar,
                    description_en=description_en,
                    config=config or {},
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_program_db", exc_info=True)
            obs.success = False
            return None
