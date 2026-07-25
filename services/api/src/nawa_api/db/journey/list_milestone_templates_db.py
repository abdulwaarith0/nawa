import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import Milestone
from nawa_api.utils.logger import get_logger


async def list_milestone_templates_db(
    *,
    program_id: uuid.UUID,
    program_cycle_id: uuid.UUID | None = None,
    session: AsyncSession | None = None,
) -> list[Milestone]:
    with observe_db(
        operation="read", table="milestones", method="list_milestone_templates_db"
    ) as obs:
        try:
            stmt = select(Milestone).where(
                Milestone.program_id == program_id, Milestone.scope == "template"
            )
            if program_cycle_id is not None:
                stmt = stmt.where(Milestone.program_cycle_id == program_cycle_id)
            stmt = stmt.order_by(Milestone.sequence)
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_milestone_templates_db", exc_info=True)
            obs.success = False
            return []
