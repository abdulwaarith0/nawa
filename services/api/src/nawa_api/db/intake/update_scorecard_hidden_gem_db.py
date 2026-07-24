import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Scorecard
from nawa_api.utils.logger import get_logger


async def update_scorecard_hidden_gem_db(
    *,
    scorecard_id: uuid.UUID,
    hidden_gem: bool,
    hidden_gem_reason_ar: str,
    hidden_gem_reason_en: str,
    session: AsyncSession | None = None,
) -> bool:
    """Hidden-gem is a scoring output, so it lives on the scorecard row (03's
    ruling) — this never touches `total_score`; it's a signal beside the
    ranking, not a correction of it."""
    with observe_db(
        operation="write", table="scorecards", method="update_scorecard_hidden_gem_db"
    ) as obs:
        try:
            stmt = (
                update(Scorecard)
                .where(Scorecard.id == scorecard_id)
                .values(
                    hidden_gem=hidden_gem,
                    hidden_gem_reason_ar=hidden_gem_reason_ar,
                    hidden_gem_reason_en=hidden_gem_reason_en,
                )
            )
            async with use_session(session) as s:
                result = await s.execute(stmt)
            obs.success = True
            return (result.rowcount or 0) > 0
        except Exception:
            get_logger().warning(
                "db_error", method="update_scorecard_hidden_gem_db", exc_info=True
            )
            obs.success = False
            return False
