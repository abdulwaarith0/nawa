import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Scorecard
from nawa_api.utils.logger import get_logger


async def create_scorecard_db(
    *,
    application_id: uuid.UUID,
    rubric_id: uuid.UUID,
    rubric_version: int,
    prompt_version: str,
    source: str,
    total_score: float,
    confidence: float | None = None,
    rationale_ar: str | None = None,
    rationale_en: str | None = None,
    hidden_gem: bool = False,
    hidden_gem_reason_ar: str | None = None,
    hidden_gem_reason_en: str | None = None,
    model: str | None = None,
    ai_call_id: uuid.UUID | None = None,
    status: str = "generated",
    session: AsyncSession | None = None,
) -> Scorecard | None:
    with observe_db(operation="write", table="scorecards", method="create_scorecard_db") as obs:
        try:
            async with use_session(session) as s:
                row = Scorecard(
                    application_id=application_id,
                    rubric_id=rubric_id,
                    rubric_version=rubric_version,
                    prompt_version=prompt_version,
                    source=source,
                    total_score=total_score,
                    confidence=confidence,
                    rationale_ar=rationale_ar,
                    rationale_en=rationale_en,
                    hidden_gem=hidden_gem,
                    hidden_gem_reason_ar=hidden_gem_reason_ar,
                    hidden_gem_reason_en=hidden_gem_reason_en,
                    model=model,
                    ai_call_id=ai_call_id,
                    status=status,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_scorecard_db", exc_info=True)
            obs.success = False
            return None
