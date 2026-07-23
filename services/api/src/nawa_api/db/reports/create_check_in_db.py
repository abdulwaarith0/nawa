import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.reports import CheckIn
from nawa_api.utils.logger import get_logger


async def create_check_in_db(
    *,
    profile_id: uuid.UUID,
    period_start: date,
    cycle_id: uuid.UUID | None = None,
    channel: str = "conversational",
    language: str = "ar",
    status: str = "scheduled",
    transcript: list | None = None,
    summary_ar: str | None = None,
    summary_en: str | None = None,
    session: AsyncSession | None = None,
) -> CheckIn | None:
    with observe_db(operation="write", table="check_ins", method="create_check_in_db") as obs:
        try:
            async with use_session(session) as s:
                row = CheckIn(
                    profile_id=profile_id,
                    period_start=period_start,
                    cycle_id=cycle_id,
                    channel=channel,
                    language=language,
                    status=status,
                    transcript=transcript or [],
                    summary_ar=summary_ar,
                    summary_en=summary_en,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_check_in_db", exc_info=True)
            obs.success = False
            return None
