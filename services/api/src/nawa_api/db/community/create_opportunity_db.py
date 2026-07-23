import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.community import Opportunity
from nawa_api.utils.logger import get_logger


async def create_opportunity_db(
    *,
    posted_by_user_id: uuid.UUID,
    kind: str,
    title_ar: str | None = None,
    title_en: str | None = None,
    description_ar: str | None = None,
    description_en: str | None = None,
    profile_id: uuid.UUID | None = None,
    org_name: str | None = None,
    location: str | None = None,
    tags: list[str] | None = None,
    domains: list[str] | None = None,
    skills: list[str] | None = None,
    deadline_at: datetime | None = None,
    status: str = "draft",
    session: AsyncSession | None = None,
) -> Opportunity | None:
    with observe_db(
        operation="write", table="opportunities", method="create_opportunity_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = Opportunity(
                    posted_by_user_id=posted_by_user_id,
                    kind=kind,
                    title_ar=title_ar,
                    title_en=title_en,
                    description_ar=description_ar,
                    description_en=description_en,
                    profile_id=profile_id,
                    org_name=org_name,
                    location=location,
                    tags=tags or [],
                    domains=domains or [],
                    skills=skills or [],
                    deadline_at=deadline_at,
                    status=status,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_opportunity_db", exc_info=True)
            obs.success = False
            return None
