import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import clamp_pagination, use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Application
from nawa_api.utils.logger import get_logger


async def list_applications_db(
    *,
    cycle_id: uuid.UUID,
    status: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    session: AsyncSession | None = None,
) -> list[Application]:
    """Canonical sort: score_desc (unscored rows sink), per ix_applications_cycle_status_score."""
    clamped_limit, clamped_offset = clamp_pagination(limit=limit, offset=offset)
    with observe_db(operation="read", table="applications", method="list_applications_db") as obs:
        try:
            stmt = select(Application).where(Application.cycle_id == cycle_id)
            if status is not None:
                stmt = stmt.where(Application.status == status)
            stmt = (
                stmt.order_by(
                    Application.ai_total_score.desc().nulls_last(),
                    Application.submitted_at.desc(),
                )
                .limit(clamped_limit)
                .offset(clamped_offset)
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_applications_db", exc_info=True)
            obs.success = False
            return []
