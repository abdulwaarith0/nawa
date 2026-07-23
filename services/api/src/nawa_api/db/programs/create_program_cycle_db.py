import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.programs import ProgramCycle
from nawa_api.utils.logger import get_logger


async def create_program_cycle_db(
    *,
    program_id: uuid.UUID,
    slug: str,
    status: str = "draft",
    name_ar: str | None = None,
    name_en: str | None = None,
    opens_at: datetime | None = None,
    closes_at: datetime | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    config: dict | None = None,
    session: AsyncSession | None = None,
) -> ProgramCycle | None:
    with observe_db(
        operation="write", table="program_cycles", method="create_program_cycle_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = ProgramCycle(
                    program_id=program_id,
                    slug=slug,
                    status=status,
                    name_ar=name_ar,
                    name_en=name_en,
                    opens_at=opens_at,
                    closes_at=closes_at,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    config=config or {},
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_program_cycle_db", exc_info=True)
            obs.success = False
            return None
