from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import User
from nawa_api.models.profiles import FounderProfile
from nawa_api.utils.logger import get_logger


async def get_profile_by_handle_db(
    *, handle: str, session: AsyncSession | None = None
) -> FounderProfile | None:
    """Public-read variant: only visible, active-owner profiles (§5 split)."""
    with observe_db(
        operation="read", table="founder_profiles", method="get_profile_by_handle_db"
    ) as obs:
        try:
            stmt = (
                select(FounderProfile)
                .join(User, User.id == FounderProfile.user_id)
                .where(
                    FounderProfile.handle == handle,
                    FounderProfile.is_public.is_(True),
                    User.is_active.is_(True),
                )
            )
            async with use_session(session) as s:
                row = (await s.execute(stmt)).scalar_one_or_none()
            obs.success = row is not None
            return row
        except Exception:
            get_logger().warning("db_error", method="get_profile_by_handle_db", exc_info=True)
            obs.success = False
            return None
