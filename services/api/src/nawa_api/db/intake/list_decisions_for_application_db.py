import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Decision
from nawa_api.utils.logger import get_logger


async def list_decisions_for_application_db(
    *, application_id: uuid.UUID, session: AsyncSession | None = None
) -> list[Decision]:
    """Append-only history, newest first — the scorecard view's decision
    timeline. The latest row wins for display; nothing here is ever deleted
    or overwritten by a re-score (03's rule)."""
    with observe_db(
        operation="read", table="decisions", method="list_decisions_for_application_db"
    ) as obs:
        try:
            stmt = (
                select(Decision)
                .where(Decision.application_id == application_id)
                .order_by(Decision.created_at.desc())
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning(
                "db_error", method="list_decisions_for_application_db", exc_info=True
            )
            obs.success = False
            return []
