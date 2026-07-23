import uuid

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Application
from nawa_api.utils.logger import get_logger


async def update_application_normalization_db(
    *,
    application_id: uuid.UUID,
    source_language: str,
    normalized: dict,
    title: str | None,
    summary: str | None,
    session: AsyncSession | None = None,
) -> bool:
    """Advance submitted → normalized: store the structured projection + promote
    title/summary + stamp normalized_at. original_answers is never touched."""
    with observe_db(
        operation="write", table="applications", method="update_application_normalization_db"
    ) as obs:
        try:
            stmt = (
                update(Application)
                .where(Application.id == application_id)
                .values(
                    source_language=source_language,
                    normalized=normalized,
                    title=title,
                    summary=summary,
                    status="normalized",
                    normalized_at=func.now(),
                )
            )
            async with use_session(session) as s:
                result = await s.execute(stmt)
            obs.success = True
            return (result.rowcount or 0) > 0
        except Exception:
            get_logger().warning(
                "db_error", method="update_application_normalization_db", exc_info=True
            )
            obs.success = False
            return False
