import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.profiles import FounderProfile
from nawa_api.utils.logger import get_logger


async def set_profile_embedding_db(
    *,
    profile_id: uuid.UUID,
    embedding: list[float],
    embedding_model: str,
    session: AsyncSession | None = None,
) -> bool:
    with observe_db(
        operation="write", table="founder_profiles", method="set_profile_embedding_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                result = await s.execute(
                    update(FounderProfile)
                    .where(FounderProfile.id == profile_id)
                    .values(
                        embedding=embedding,
                        embedding_model=embedding_model,
                        embedding_stale=False,
                    )
                )
            obs.success = result.rowcount > 0
            return obs.success
        except Exception:
            get_logger().warning("db_error", method="set_profile_embedding_db", exc_info=True)
            obs.success = False
            return False
