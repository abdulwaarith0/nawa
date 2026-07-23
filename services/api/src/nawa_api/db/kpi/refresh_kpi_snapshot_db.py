import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.profiles import FounderProfile
from nawa_api.models.reports import KpiDefinition, KpiEntry
from nawa_api.utils.logger import get_logger


async def refresh_kpi_snapshot_db(
    *, profile_id: uuid.UUID, session: AsyncSession | None = None
) -> bool:
    """Recomputes founder_profiles.kpi_snapshot from kpi_entries — the ONLY
    writer of that column. Latest entry + prior-period delta per kpi_key, in
    one SQL statement using a ROW_NUMBER() window function."""
    with observe_db(
        operation="write", table="founder_profiles", method="refresh_kpi_snapshot_db"
    ) as obs:
        try:
            row_number = (
                func.row_number()
                .over(
                    partition_by=KpiEntry.kpi_definition_id,
                    order_by=KpiEntry.period_start.desc(),
                )
                .label("rn")
            )
            subq = (
                select(
                    KpiEntry.kpi_definition_id,
                    KpiEntry.period_start,
                    KpiEntry.value,
                    KpiDefinition.key,
                    row_number,
                )
                .join(KpiDefinition, KpiDefinition.id == KpiEntry.kpi_definition_id)
                .where(KpiEntry.profile_id == profile_id)
                .subquery()
            )
            stmt = select(subq).where(subq.c.rn <= 2).order_by(subq.c.key, subq.c.rn)

            async with use_session(session) as s:
                rows = (await s.execute(stmt)).all()

                by_key: dict[str, list] = {}
                for r in rows:
                    by_key.setdefault(r.key, []).append(r)

                snapshot: dict[str, dict] = {}
                for key, entries in by_key.items():
                    latest = entries[0]
                    previous = entries[1] if len(entries) > 1 else None
                    delta_pct = None
                    if previous is not None and previous.value:
                        delta_pct = float((latest.value - previous.value) / previous.value * 100)
                    snapshot[key] = {
                        "value": float(latest.value),
                        "period_start": latest.period_start.isoformat(),
                        "delta_pct": delta_pct,
                    }

                await s.execute(
                    update(FounderProfile)
                    .where(FounderProfile.id == profile_id)
                    .values(kpi_snapshot=snapshot, kpi_snapshot_at=func.now())
                )
            obs.success = True
            return True
        except Exception:
            get_logger().warning("db_error", method="refresh_kpi_snapshot_db", exc_info=True)
            obs.success = False
            return False
