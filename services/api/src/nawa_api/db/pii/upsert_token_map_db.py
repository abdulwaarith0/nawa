import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.ai import PiiTokenMap
from nawa_api.utils.logger import get_logger


async def upsert_token_map_db(
    *,
    subject_type: str,
    subject_id: uuid.UUID,
    tokens: dict,
    session: AsyncSession | None = None,
) -> PiiTokenMap | None:
    """Insert or replace a subject's token map (unique on subject_type+id).
    Returns the persisted row, or None on error."""
    with observe_db(operation="write", table="pii_token_maps", method="upsert_token_map_db") as obs:
        try:
            async with use_session(session) as s:
                stmt = (
                    insert(PiiTokenMap)
                    .values(subject_type=subject_type, subject_id=subject_id, tokens=tokens)
                    .on_conflict_do_update(
                        index_elements=["subject_type", "subject_id"],
                        set_={"tokens": tokens, "updated_at": func.now()},
                    )
                )
                await s.execute(stmt)
                row = (
                    await s.execute(
                        select(PiiTokenMap).where(
                            PiiTokenMap.subject_type == subject_type,
                            PiiTokenMap.subject_id == subject_id,
                        )
                    )
                ).scalar_one()
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="upsert_token_map_db", exc_info=True)
            obs.success = False
            return None
