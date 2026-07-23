"""Filtered pgvector retrieval over resource_chunks (05-ai-infrastructure.md §9.3).

The HNSW cosine index is owned by 03-data-spine.md's migration; this only
queries it via the `<=>` cosine-distance operator. Metadata filtering happens
in-database (WHERE clauses), never post-hoc in Python. Degrades to [] on error.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import Resource, ResourceChunk
from nawa_api.utils.logger import get_logger


async def search_chunks_db(
    *,
    query_embedding: list[float],
    k: int = 8,
    program_id: str | None = None,
    language: str | None = None,
    resource_type: str | None = None,
    audience: str | None = None,
    session: AsyncSession | None = None,
) -> list[tuple[ResourceChunk, float]]:
    """k-NN over live resources' chunks, returning (chunk, score) where
    score = 1 - cosine distance, ordered nearest-first."""
    with observe_db(operation="read", table="resource_chunks", method="search_chunks_db") as obs:
        try:
            distance = ResourceChunk.embedding.cosine_distance(query_embedding)
            stmt = (
                select(ResourceChunk, distance.label("distance"))
                .join(Resource, Resource.id == ResourceChunk.resource_id)
                .where(Resource.status == "live", ResourceChunk.embedding.is_not(None))
            )
            if language is not None:
                stmt = stmt.where(ResourceChunk.language == language)
            if resource_type is not None:
                stmt = stmt.where(Resource.kind == resource_type)
            if program_id is not None:
                stmt = stmt.where(
                    ResourceChunk.chunk_metadata["program_id"].astext == program_id
                )
            if audience is not None:
                stmt = stmt.where(ResourceChunk.chunk_metadata["audience"].astext == audience)
            stmt = stmt.order_by(distance).limit(k)

            async with use_session(session) as s:
                rows = (await s.execute(stmt)).all()
            obs.success = True
            return [(row.ResourceChunk, 1 - row.distance) for row in rows]
        except Exception:
            get_logger().warning("db_error", method="search_chunks_db", exc_info=True)
            obs.success = False
            return []
