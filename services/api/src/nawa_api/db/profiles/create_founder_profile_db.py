import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.profiles import FounderProfile
from nawa_api.utils.logger import get_logger


async def create_founder_profile_db(
    *,
    user_id: uuid.UUID,
    handle: str,
    display_name_ar: str | None = None,
    display_name_en: str | None = None,
    venture_name_ar: str | None = None,
    venture_name_en: str | None = None,
    venture_summary_ar: str | None = None,
    venture_summary_en: str | None = None,
    sector: str | None = None,
    country: str | None = None,
    city: str | None = None,
    stage: str = "idea",
    skills: list[str] | None = None,
    domains: list[str] | None = None,
    session: AsyncSession | None = None,
) -> FounderProfile | None:
    with observe_db(
        operation="write", table="founder_profiles", method="create_founder_profile_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = FounderProfile(
                    user_id=user_id,
                    handle=handle,
                    display_name_ar=display_name_ar,
                    display_name_en=display_name_en,
                    venture_name_ar=venture_name_ar,
                    venture_name_en=venture_name_en,
                    venture_summary_ar=venture_summary_ar,
                    venture_summary_en=venture_summary_en,
                    sector=sector,
                    country=country,
                    city=city,
                    stage=stage,
                    skills=skills or [],
                    domains=domains or [],
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_founder_profile_db", exc_info=True)
            obs.success = False
            return None
