import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.ai import ApplicationEmbedding
from nawa_api.utils.logger import get_logger


async def get_application_embedding_db(
    *, application_id: uuid.UUID, session: AsyncSession | None = None
) -> ApplicationEmbedding | None:
    with observe_db(
        operation="read", table="application_embeddings", method="get_application_embedding_db"
    ) as obs:
        try:
            stmt = select(ApplicationEmbedding).where(
                ApplicationEmbedding.application_id == application_id
            )
            async with use_session(session) as s:
                row = (await s.execute(stmt)).scalar_one_or_none()
            obs.success = row is not None
            return row
        except Exception:
            get_logger().warning(
                "db_error", method="get_application_embedding_db", exc_info=True
            )
            obs.success = False
            return None
