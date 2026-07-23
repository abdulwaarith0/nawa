import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import ScorecardCriterion
from nawa_api.utils.logger import get_logger


async def create_scorecard_criterion_db(
    *,
    scorecard_id: uuid.UUID,
    criterion_key: str,
    score: float,
    weight: float,
    rationale_ar: str | None = None,
    rationale_en: str | None = None,
    citations: list | None = None,
    session: AsyncSession | None = None,
) -> ScorecardCriterion | None:
    with observe_db(
        operation="write", table="scorecard_criteria", method="create_scorecard_criterion_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = ScorecardCriterion(
                    scorecard_id=scorecard_id,
                    criterion_key=criterion_key,
                    score=score,
                    weight=weight,
                    rationale_ar=rationale_ar,
                    rationale_en=rationale_en,
                    citations=citations or [],
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_scorecard_criterion_db", exc_info=True)
            obs.success = False
            return None
