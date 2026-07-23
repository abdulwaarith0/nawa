import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import ResourceChunk
from nawa_api.utils.logger import get_logger


async def list_chunk_fingerprints_db(
    *, resource_id: uuid.UUID, session: AsyncSession | None = None
) -> dict[int, tuple[str, str | None]]:
    """chunk_index -> (source_hash, embedding_model) for a resource's chunks.

    The embed pipeline uses this to skip re-embedding content that hasn't changed
    (seed pseudo-vectors carry embedding_model='seed', so they never match a real
    model and are always replaced on the first live/mock pass)."""
    with observe_db(
        operation="read", table="resource_chunks", method="list_chunk_fingerprints_db"
    ) as obs:
        try:
            stmt = select(
                ResourceChunk.chunk_index,
                ResourceChunk.source_hash,
                ResourceChunk.embedding_model,
            ).where(ResourceChunk.resource_id == resource_id)
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).all()
            obs.success = True
            return {r.chunk_index: (r.source_hash, r.embedding_model) for r in rows}
        except Exception:
            get_logger().warning("db_error", method="list_chunk_fingerprints_db", exc_info=True)
            obs.success = False
            return {}
