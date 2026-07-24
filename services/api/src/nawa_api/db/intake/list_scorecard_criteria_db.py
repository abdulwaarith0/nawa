import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import ScorecardCriterion
from nawa_api.utils.logger import get_logger


async def list_scorecard_criteria_db(
    *, scorecard_ids: list[uuid.UUID], session: AsyncSession | None = None
) -> list[ScorecardCriterion]:
    """Batch fetch so a shortlist page (up to 100 scorecards) costs one query,
    not one-per-row; a single scorecard's criteria is just a one-element list."""
    if not scorecard_ids:
        return []
    with observe_db(
        operation="read", table="scorecard_criteria", method="list_scorecard_criteria_db"
    ) as obs:
        try:
            stmt = select(ScorecardCriterion).where(
                ScorecardCriterion.scorecard_id.in_(scorecard_ids)
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning(
                "db_error", method="list_scorecard_criteria_db", exc_info=True
            )
            obs.success = False
            return []
