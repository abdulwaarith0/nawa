import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import clamp_pagination, use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.programs import ProgramCycle
from nawa_api.utils.logger import get_logger


async def list_program_cycles_db(
    *,
    program_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    session: AsyncSession | None = None,
) -> list[ProgramCycle]:
    clamped_limit, clamped_offset = clamp_pagination(limit=limit, offset=offset)
    with observe_db(
        operation="read", table="program_cycles", method="list_program_cycles_db"
    ) as obs:
        try:
            stmt = select(ProgramCycle)
            if program_id is not None:
                stmt = stmt.where(ProgramCycle.program_id == program_id)
            if status is not None:
                stmt = stmt.where(ProgramCycle.status == status)
            stmt = (
                stmt.order_by(ProgramCycle.opens_at.desc())
                .limit(clamped_limit)
                .offset(clamped_offset)
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_program_cycles_db", exc_info=True)
            obs.success = False
            return []
