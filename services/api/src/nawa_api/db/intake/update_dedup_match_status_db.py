import uuid

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import DedupMatch
from nawa_api.utils.logger import get_logger


async def update_dedup_match_status_db(
    *,
    match_id: uuid.UUID,
    status: str,
    reviewed_by: uuid.UUID,
    session: AsyncSession | None = None,
) -> bool:
    with observe_db(
        operation="write", table="dedup_matches", method="update_dedup_match_status_db"
    ) as obs:
        try:
            stmt = (
                update(DedupMatch)
                .where(DedupMatch.id == match_id)
                .values(status=status, reviewed_by=reviewed_by, reviewed_at=func.now())
            )
            async with use_session(session) as s:
                result = await s.execute(stmt)
            obs.success = True
            return (result.rowcount or 0) > 0
        except Exception:
            get_logger().warning(
                "db_error", method="update_dedup_match_status_db", exc_info=True
            )
            obs.success = False
            return False
