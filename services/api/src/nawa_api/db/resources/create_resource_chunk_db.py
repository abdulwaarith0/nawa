import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import ResourceChunk
from nawa_api.utils.logger import get_logger


async def create_resource_chunk_db(
    *,
    resource_id: uuid.UUID,
    chunk_index: int,
    content: str,
    token_count: int,
    source_hash: str,
    language: str = "ar",
    heading_path: list[str] | None = None,
    embedding: list[float] | None = None,
    embedding_model: str | None = None,
    session: AsyncSession | None = None,
) -> ResourceChunk | None:
    with observe_db(
        operation="write", table="resource_chunks", method="create_resource_chunk_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = ResourceChunk(
                    resource_id=resource_id,
                    chunk_index=chunk_index,
                    content=content,
                    token_count=token_count,
                    source_hash=source_hash,
                    language=language,
                    heading_path=heading_path or [],
                    embedding=embedding,
                    embedding_model=embedding_model,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_resource_chunk_db", exc_info=True)
            obs.success = False
            return None
