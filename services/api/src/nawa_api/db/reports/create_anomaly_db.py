import uuid
from datetime import date

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.reports import Anomaly
from nawa_api.utils.logger import get_logger


async def create_anomaly_db(
    *,
    profile_id: uuid.UUID,
    kind: str,
    severity: str,
    window_start: date,
    window_end: date,
    dedupe_key: str,
    kpi_definition_id: uuid.UUID | None = None,
    details: dict | None = None,
    status: str = "open",
    session: AsyncSession | None = None,
) -> bool:
    """Upserts by dedupe_key: a scan escalates/updates the open row instead of
    stacking duplicates (the partial unique index enforces one open row per
    profile+kind)."""
    with observe_db(operation="write", table="anomalies", method="create_anomaly_db") as obs:
        try:
            stmt = insert(Anomaly).values(
                profile_id=profile_id,
                kpi_definition_id=kpi_definition_id,
                kind=kind,
                severity=severity,
                window_start=window_start,
                window_end=window_end,
                details=details or {},
                dedupe_key=dedupe_key,
                status=status,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[Anomaly.dedupe_key],
                set_={
                    "severity": severity,
                    "window_end": window_end,
                    "details": details or {},
                },
            )
            async with use_session(session) as s:
                await s.execute(stmt)
            obs.success = True
            return True
        except Exception:
            get_logger().warning("db_error", method="create_anomaly_db", exc_info=True)
            obs.success = False
            return False
