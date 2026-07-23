import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.community import Request
from nawa_api.utils.logger import get_logger


async def create_request_db(
    *,
    profile_id: uuid.UUID,
    kind: str,
    title_ar: str | None = None,
    title_en: str | None = None,
    details_ar: str | None = None,
    details_en: str | None = None,
    skills_needed: list[str] | None = None,
    duration_label: str | None = None,
    source: str = "member",
    status: str = "draft",
    session: AsyncSession | None = None,
) -> Request | None:
    with observe_db(operation="write", table="requests", method="create_request_db") as obs:
        try:
            async with use_session(session) as s:
                row = Request(
                    profile_id=profile_id,
                    kind=kind,
                    title_ar=title_ar,
                    title_en=title_en,
                    details_ar=details_ar,
                    details_en=details_en,
                    skills_needed=skills_needed or [],
                    duration_label=duration_label,
                    source=source,
                    status=status,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_request_db", exc_info=True)
            obs.success = False
            return None
