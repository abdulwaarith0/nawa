import uuid
from datetime import date, datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.reports import KpiEntry
from nawa_api.utils.logger import get_logger


async def create_kpi_entry_db(
    *,
    profile_id: uuid.UUID,
    kpi_definition_id: uuid.UUID,
    period_start: date,
    value: float,
    confirmed_at: datetime,
    source: str = "check_in",
    check_in_id: uuid.UUID | None = None,
    created_by_user_id: uuid.UUID | None = None,
    note: str | None = None,
    session: AsyncSession | None = None,
) -> bool:
    """Corrections upsert on (profile_id, kpi_definition_id, period_start) —
    the time-series is append-only, but a given period's row is unique."""
    with observe_db(operation="write", table="kpi_entries", method="create_kpi_entry_db") as obs:
        try:
            stmt = insert(KpiEntry).values(
                profile_id=profile_id,
                kpi_definition_id=kpi_definition_id,
                period_start=period_start,
                value=value,
                confirmed_at=confirmed_at,
                source=source,
                check_in_id=check_in_id,
                created_by_user_id=created_by_user_id,
                note=note,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[
                    KpiEntry.profile_id,
                    KpiEntry.kpi_definition_id,
                    KpiEntry.period_start,
                ],
                set_={"value": value, "confirmed_at": confirmed_at, "source": source},
            )
            async with use_session(session) as s:
                await s.execute(stmt)
            obs.success = True
            return True
        except Exception:
            get_logger().warning("db_error", method="create_kpi_entry_db", exc_info=True)
            obs.success = False
            return False
