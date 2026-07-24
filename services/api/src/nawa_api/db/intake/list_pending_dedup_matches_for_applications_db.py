import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import DedupMatch
from nawa_api.utils.logger import get_logger


async def list_pending_dedup_matches_for_applications_db(
    *, application_ids: list[uuid.UUID], session: AsyncSession | None = None
) -> list[DedupMatch]:
    """Batch version of the pending-dedup check for a whole shortlist page —
    one query instead of one per row. A match may touch a page application
    from either side of the pair."""
    if not application_ids:
        return []
    with observe_db(
        operation="read",
        table="dedup_matches",
        method="list_pending_dedup_matches_for_applications_db",
    ) as obs:
        try:
            stmt = select(DedupMatch).where(
                DedupMatch.status == "pending",
                or_(
                    DedupMatch.application_id.in_(application_ids),
                    DedupMatch.matched_application_id.in_(application_ids),
                ),
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning(
                "db_error",
                method="list_pending_dedup_matches_for_applications_db",
                exc_info=True,
            )
            obs.success = False
            return []
