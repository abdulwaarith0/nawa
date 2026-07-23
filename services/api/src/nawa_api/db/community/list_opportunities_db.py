from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import clamp_pagination, use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.community import Opportunity
from nawa_api.utils.logger import get_logger


async def list_opportunities_db(
    *,
    status: str | None = "open",
    limit: int | None = None,
    offset: int | None = None,
    session: AsyncSession | None = None,
) -> list[Opportunity]:
    """Canonical sort: closing_soon (open items, nearest deadline first)."""
    clamped_limit, clamped_offset = clamp_pagination(limit=limit, offset=offset)
    with observe_db(operation="read", table="opportunities", method="list_opportunities_db") as obs:
        try:
            stmt = select(Opportunity)
            if status is not None:
                stmt = stmt.where(Opportunity.status == status)
            stmt = (
                stmt.order_by(
                    Opportunity.deadline_at.asc().nulls_last(), Opportunity.created_at.desc()
                )
                .limit(clamped_limit)
                .offset(clamped_offset)
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_opportunities_db", exc_info=True)
            obs.success = False
            return []
