import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import DedupMatch
from nawa_api.utils.logger import get_logger


async def list_dedup_matches_db(
    *, application_id: uuid.UUID, session: AsyncSession | None = None
) -> list[DedupMatch]:
    """Both directions: a match may have been recorded from either side of
    the pair depending on which application the scan ran against first."""
    with observe_db(
        operation="read", table="dedup_matches", method="list_dedup_matches_db"
    ) as obs:
        try:
            stmt = (
                select(DedupMatch)
                .where(
                    or_(
                        DedupMatch.application_id == application_id,
                        DedupMatch.matched_application_id == application_id,
                    )
                )
                .order_by(DedupMatch.similarity.desc())
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_dedup_matches_db", exc_info=True)
            obs.success = False
            return []
