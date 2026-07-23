import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Application
from nawa_api.utils.logger import get_logger


async def create_application_db(
    *,
    cycle_id: uuid.UUID,
    applicant_name: str,
    applicant_email: str,
    source_language: str,
    original_answers: dict,
    profile_id: uuid.UUID | None = None,
    source_upload_id: uuid.UUID | None = None,
    raw_extra: dict | None = None,
    status: str = "submitted",
    submitted_at: datetime | None = None,
    session: AsyncSession | None = None,
) -> Application | None:
    with observe_db(operation="write", table="applications", method="create_application_db") as obs:
        try:
            async with use_session(session) as s:
                row = Application(
                    cycle_id=cycle_id,
                    applicant_name=applicant_name,
                    applicant_email=applicant_email,
                    source_language=source_language,
                    original_answers=original_answers,
                    profile_id=profile_id,
                    source_upload_id=source_upload_id,
                    raw_extra=raw_extra or {},
                    status=status,
                    **({"submitted_at": submitted_at} if submitted_at is not None else {}),
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_application_db", exc_info=True)
            obs.success = False
            return None
