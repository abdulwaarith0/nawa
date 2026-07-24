import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Application
from nawa_api.utils.logger import get_logger


async def update_application_profile_link_db(
    *, application_id: uuid.UUID, profile_id: uuid.UUID, session: AsyncSession | None = None
) -> bool:
    """03's canon name for the founder-profile linkage — set once, on
    acceptance (06-intake-copilot.md §6.2)."""
    with observe_db(
        operation="write", table="applications", method="update_application_profile_link_db"
    ) as obs:
        try:
            stmt = (
                update(Application)
                .where(Application.id == application_id)
                .values(profile_id=profile_id)
            )
            async with use_session(session) as s:
                result = await s.execute(stmt)
            obs.success = True
            return (result.rowcount or 0) > 0
        except Exception:
            get_logger().warning(
                "db_error", method="update_application_profile_link_db", exc_info=True
            )
            obs.success = False
            return False
