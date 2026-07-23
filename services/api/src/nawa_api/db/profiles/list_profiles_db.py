from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import clamp_pagination, use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.profiles import FounderProfile
from nawa_api.utils.logger import get_logger


async def list_profiles_db(
    *,
    country: str | None = None,
    sector: str | None = None,
    skills: list[str] | None = None,
    limit: int | None = None,
    offset: int | None = None,
    session: AsyncSession | None = None,
) -> list[FounderProfile]:
    """Directory read: is_public only, canonical sort recently_active."""
    clamped_limit, clamped_offset = clamp_pagination(limit=limit, offset=offset)
    with observe_db(operation="read", table="founder_profiles", method="list_profiles_db") as obs:
        try:
            stmt = select(FounderProfile).where(FounderProfile.is_public.is_(True))
            if country is not None:
                stmt = stmt.where(FounderProfile.country == country)
            if sector is not None:
                stmt = stmt.where(FounderProfile.sector == sector)
            if skills:
                stmt = stmt.where(FounderProfile.skills.overlap(skills))
            stmt = (
                stmt.order_by(FounderProfile.updated_at.desc())
                .limit(clamped_limit)
                .offset(clamped_offset)
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_profiles_db", exc_info=True)
            obs.success = False
            return []
