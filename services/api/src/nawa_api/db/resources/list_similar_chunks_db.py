from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import Resource, ResourceChunk
from nawa_api.utils.logger import get_logger


async def list_similar_chunks_db(
    *, query_embedding: list[float], k: int = 8, session: AsyncSession | None = None
) -> list[tuple[ResourceChunk, float]]:
    """k-NN over resource_chunks joined to live resources only (public-read split)."""
    with observe_db(
        operation="read", table="resource_chunks", method="list_similar_chunks_db"
    ) as obs:
        try:
            distance = ResourceChunk.embedding.cosine_distance(query_embedding)
            stmt = (
                select(ResourceChunk, distance.label("distance"))
                .join(Resource, Resource.id == ResourceChunk.resource_id)
                .where(Resource.status == "live", ResourceChunk.embedding.is_not(None))
                .order_by(distance)
                .limit(k)
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).all()
            obs.success = True
            return [(row.ResourceChunk, 1 - row.distance) for row in rows]
        except Exception:
            get_logger().warning("db_error", method="list_similar_chunks_db", exc_info=True)
            obs.success = False
            return []
