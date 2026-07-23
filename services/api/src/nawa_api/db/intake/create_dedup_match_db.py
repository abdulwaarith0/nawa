import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import DedupMatch
from nawa_api.utils.logger import get_logger


async def create_dedup_match_db(
    *,
    application_id: uuid.UUID,
    matched_application_id: uuid.UUID,
    similarity: float,
    status: str = "pending",
    session: AsyncSession | None = None,
) -> DedupMatch | None:
    with observe_db(
        operation="write", table="dedup_matches", method="create_dedup_match_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = DedupMatch(
                    application_id=application_id,
                    matched_application_id=matched_application_id,
                    similarity=similarity,
                    status=status,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_dedup_match_db", exc_info=True)
            obs.success = False
            return None
