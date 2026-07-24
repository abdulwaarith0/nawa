import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import DedupMatch
from nawa_api.utils.logger import get_logger


async def upsert_dedup_match_db(
    *,
    application_id: uuid.UUID,
    matched_application_id: uuid.UUID,
    similarity: float,
    session: AsyncSession | None = None,
) -> bool:
    """Idempotent on the unique `(application_id, matched_application_id)` pair
    so re-running a dedup scan converges instead of erroring or piling up rows.
    Only `similarity` is refreshed on conflict — `status`/`reviewed_by`/
    `reviewed_at` are never touched here, so a human's review decision is
    never clobbered by a later re-scan."""
    with observe_db(
        operation="write", table="dedup_matches", method="upsert_dedup_match_db"
    ) as obs:
        try:
            stmt = insert(DedupMatch).values(
                application_id=application_id,
                matched_application_id=matched_application_id,
                similarity=similarity,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[DedupMatch.application_id, DedupMatch.matched_application_id],
                set_={"similarity": stmt.excluded.similarity},
            )
            async with use_session(session) as s:
                await s.execute(stmt)
            obs.success = True
            return True
        except Exception:
            get_logger().warning("db_error", method="upsert_dedup_match_db", exc_info=True)
            obs.success = False
            return False
