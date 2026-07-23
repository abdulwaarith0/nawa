import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.ai import ApplicationEmbedding
from nawa_api.utils.logger import get_logger


async def list_similar_applications_db(
    *, application_id: uuid.UUID, k: int = 5, session: AsyncSession | None = None
) -> list[tuple[uuid.UUID, float]]:
    """k-NN over application_embeddings via pgvector cosine distance, excluding
    self, returning (matched_application_id, similarity) pairs, best first."""
    with observe_db(
        operation="read",
        table="application_embeddings",
        method="list_similar_applications_db",
    ) as obs:
        try:
            async with use_session(session) as s:
                self_row = (
                    await s.execute(
                        select(ApplicationEmbedding.embedding).where(
                            ApplicationEmbedding.application_id == application_id
                        )
                    )
                ).scalar_one_or_none()
                if self_row is None:
                    obs.success = False
                    return []

                distance = ApplicationEmbedding.embedding.cosine_distance(self_row)
                stmt = (
                    select(ApplicationEmbedding.application_id, distance.label("distance"))
                    .where(ApplicationEmbedding.application_id != application_id)
                    .order_by(distance)
                    .limit(k)
                )
                rows = (await s.execute(stmt)).all()
            obs.success = True
            return [(row.application_id, 1 - row.distance) for row in rows]
        except Exception:
            get_logger().warning("db_error", method="list_similar_applications_db", exc_info=True)
            obs.success = False
            return []
