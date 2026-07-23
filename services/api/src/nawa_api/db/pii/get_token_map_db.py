import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.ai import PiiTokenMap
from nawa_api.utils.logger import get_logger


async def get_token_map_db(
    *,
    subject_type: str,
    subject_id: uuid.UUID,
    session: AsyncSession | None = None,
) -> PiiTokenMap | None:
    """Load the persisted pseudonymizer mapping for a subject, or None."""
    with observe_db(operation="read", table="pii_token_maps", method="get_token_map_db") as obs:
        try:
            async with use_session(session) as s:
                result = await s.execute(
                    select(PiiTokenMap).where(
                        PiiTokenMap.subject_type == subject_type,
                        PiiTokenMap.subject_id == subject_id,
                    )
                )
                row = result.scalar_one_or_none()
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="get_token_map_db", exc_info=True)
            obs.success = False
            return None
