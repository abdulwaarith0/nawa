import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.reports import KpiDefinition
from nawa_api.utils.logger import get_logger


async def create_kpi_definition_db(
    *,
    key: str,
    name_ar: str | None = None,
    name_en: str | None = None,
    unit: str | None = None,
    direction: str = "up_good",
    value_type: str = "number",
    aggregation: str = "last",
    program_id: uuid.UUID | None = None,
    config: dict | None = None,
    session: AsyncSession | None = None,
) -> KpiDefinition | None:
    with observe_db(
        operation="write", table="kpi_definitions", method="create_kpi_definition_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = KpiDefinition(
                    key=key,
                    name_ar=name_ar,
                    name_en=name_en,
                    unit=unit,
                    direction=direction,
                    value_type=value_type,
                    aggregation=aggregation,
                    program_id=program_id,
                    config=config or {},
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_kpi_definition_db", exc_info=True)
            obs.success = False
            return None
