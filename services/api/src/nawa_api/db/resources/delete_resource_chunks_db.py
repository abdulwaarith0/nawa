import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import ResourceChunk
from nawa_api.utils.logger import get_logger


async def delete_resource_chunks_db(
    *, resource_id: uuid.UUID, session: AsyncSession | None = None
) -> int:
    """Remove all chunks for a resource (the embed job re-inserts fresh ones)."""
    with observe_db(
        operation="write", table="resource_chunks", method="delete_resource_chunks_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                result = await s.execute(
                    delete(ResourceChunk).where(ResourceChunk.resource_id == resource_id)
                )
            obs.success = True
            return result.rowcount or 0
        except Exception:
            get_logger().warning("db_error", method="delete_resource_chunks_db", exc_info=True)
            obs.success = False
            return 0
