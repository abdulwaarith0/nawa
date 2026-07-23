import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.reports import KpiEntry
from nawa_api.utils.logger import get_logger


async def list_kpi_series_db(
    *,
    profile_id: uuid.UUID,
    kpi_definition_id: uuid.UUID,
    period_from: date | None = None,
    period_to: date | None = None,
    session: AsyncSession | None = None,
) -> list[KpiEntry]:
    """A profile's sparkline, canonical sort period_desc (newest first)."""
    with observe_db(operation="read", table="kpi_entries", method="list_kpi_series_db") as obs:
        try:
            stmt = select(KpiEntry).where(
                KpiEntry.profile_id == profile_id,
                KpiEntry.kpi_definition_id == kpi_definition_id,
            )
            if period_from is not None:
                stmt = stmt.where(KpiEntry.period_start >= period_from)
            if period_to is not None:
                stmt = stmt.where(KpiEntry.period_start <= period_to)
            stmt = stmt.order_by(KpiEntry.period_start.desc())
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_kpi_series_db", exc_info=True)
            obs.success = False
            return []
