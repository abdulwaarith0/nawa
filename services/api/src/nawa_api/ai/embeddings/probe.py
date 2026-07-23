"""Boot probe: the live resource_chunks.embedding column must match
EMBEDDINGS_DIMENSION (05-ai-infrastructure.md §4). A mismatch means a provider
was swapped without the required migration — log a loud ERROR.

For pgvector, a column's declared dimension is stored directly in atttypmod.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.ai.embeddings.base import EMBEDDINGS_DIMENSION
from nawa_api.utils.logger import get_logger

_ATTTYPMOD_SQL = text(
    "SELECT a.atttypmod FROM pg_attribute a "
    "JOIN pg_class c ON c.oid = a.attrelid "
    "WHERE c.relname = 'resource_chunks' AND a.attname = 'embedding'"
)


async def check_embedding_dimension(session: AsyncSession) -> bool:
    declared = (await session.execute(_ATTTYPMOD_SQL)).scalar_one_or_none()
    if declared is None:
        get_logger().error("embedding_column_missing")
        return False
    if declared != EMBEDDINGS_DIMENSION:
        get_logger().error(
            "embedding_dimension_mismatch", declared=declared, expected=EMBEDDINGS_DIMENSION
        )
        return False
    return True
