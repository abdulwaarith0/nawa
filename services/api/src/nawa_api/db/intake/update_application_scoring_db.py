import uuid

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Application
from nawa_api.utils.logger import get_logger


async def update_application_scoring_db(
    *, application_id: uuid.UUID, total_score: float, session: AsyncSession | None = None
) -> bool:
    """Advance normalized -> scored: stamp ai_total_score + scored_at. The
    scorecard/scorecard_criteria rows themselves are written separately
    (create_scorecard_db / create_scorecard_criterion_db) — this only advances
    the application's own denormalized status + score columns."""
    with observe_db(
        operation="write", table="applications", method="update_application_scoring_db"
    ) as obs:
        try:
            stmt = (
                update(Application)
                .where(Application.id == application_id)
                .values(status="scored", ai_total_score=total_score, scored_at=func.now())
            )
            async with use_session(session) as s:
                result = await s.execute(stmt)
            obs.success = True
            return (result.rowcount or 0) > 0
        except Exception:
            get_logger().warning(
                "db_error", method="update_application_scoring_db", exc_info=True
            )
            obs.success = False
            return False
