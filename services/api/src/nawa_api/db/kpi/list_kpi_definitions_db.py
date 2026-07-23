from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.reports import KpiDefinition
from nawa_api.utils.logger import get_logger


async def list_kpi_definitions_db(
    *, is_active: bool | None = True, session: AsyncSession | None = None
) -> list[KpiDefinition]:
    with observe_db(
        operation="read", table="kpi_definitions", method="list_kpi_definitions_db"
    ) as obs:
        try:
            stmt = select(KpiDefinition)
            if is_active is not None:
                stmt = stmt.where(KpiDefinition.is_active == is_active)
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_kpi_definitions_db", exc_info=True)
            obs.success = False
            return []
