from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.profiles import FounderProfile
from nawa_api.utils.logger import get_logger


async def get_profile_by_handle_any_status_db(
    *, handle: str, session: AsyncSession | None = None
) -> FounderProfile | None:
    """Ownership/staff-read variant: no visibility filter, keyed by handle
    (§5 split — the counterpart of `get_profile_by_id_any_status_db`)."""
    with observe_db(
        operation="read", table="founder_profiles", method="get_profile_by_handle_any_status_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = (
                    await s.execute(select(FounderProfile).where(FounderProfile.handle == handle))
                ).scalar_one_or_none()
            obs.success = row is not None
            return row
        except Exception:
            get_logger().warning(
                "db_error", method="get_profile_by_handle_any_status_db", exc_info=True
            )
            obs.success = False
            return None
