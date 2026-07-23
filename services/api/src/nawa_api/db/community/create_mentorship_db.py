import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.community import Mentorship
from nawa_api.utils.logger import get_logger


async def create_mentorship_db(
    *,
    mentor_profile_id: uuid.UUID,
    mentee_profile_id: uuid.UUID,
    cohort_id: uuid.UUID | None = None,
    matched_by: str = "ai",
    score: float | None = None,
    rationale_ar: str | None = None,
    rationale_en: str | None = None,
    status: str = "suggested",
    session: AsyncSession | None = None,
) -> Mentorship | None:
    with observe_db(operation="write", table="mentorships", method="create_mentorship_db") as obs:
        try:
            async with use_session(session) as s:
                row = Mentorship(
                    mentor_profile_id=mentor_profile_id,
                    mentee_profile_id=mentee_profile_id,
                    cohort_id=cohort_id,
                    matched_by=matched_by,
                    score=score,
                    rationale_ar=rationale_ar,
                    rationale_en=rationale_en,
                    status=status,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_mentorship_db", exc_info=True)
            obs.success = False
            return None
