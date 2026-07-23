import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.ai import ApplicationEmbedding
from nawa_api.utils.logger import get_logger


async def create_application_embedding_db(
    *,
    application_id: uuid.UUID,
    embedding: list[float],
    embedding_model: str,
    source_hash: str,
    session: AsyncSession | None = None,
) -> bool:
    """Upserts by application_id (1:1 side-table; re-embeds replace the row)."""
    with observe_db(
        operation="write",
        table="application_embeddings",
        method="create_application_embedding_db",
    ) as obs:
        try:
            stmt = insert(ApplicationEmbedding).values(
                application_id=application_id,
                embedding=embedding,
                embedding_model=embedding_model,
                source_hash=source_hash,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[ApplicationEmbedding.application_id],
                set_={
                    "embedding": embedding,
                    "embedding_model": embedding_model,
                    "source_hash": source_hash,
                },
            )
            async with use_session(session) as s:
                await s.execute(stmt)
            obs.success = True
            return True
        except Exception:
            get_logger().warning(
                "db_error", method="create_application_embedding_db", exc_info=True
            )
            obs.success = False
            return False
