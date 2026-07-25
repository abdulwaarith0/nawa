import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import MilestoneProgress
from nawa_api.utils.logger import get_logger

_PATCHABLE_FIELDS = frozenset(
    {"status", "note_ar", "note_en", "evidence_links", "reviewed_by_user_id"}
)


async def update_milestone_progress_db(
    *,
    progress_id: uuid.UUID,
    patch: dict[str, str | list | None],
    updated_by_user_id: uuid.UUID,
    session: AsyncSession | None = None,
) -> bool:
    values = {k: v for k, v in patch.items() if k in _PATCHABLE_FIELDS}
    values["updated_by_user_id"] = updated_by_user_id
    with observe_db(
        operation="write", table="milestone_progress", method="update_milestone_progress_db"
    ) as obs:
        try:
            stmt = (
                update(MilestoneProgress)
                .where(MilestoneProgress.id == progress_id)
                .values(**values)
            )
            async with use_session(session) as s:
                result = await s.execute(stmt)
            obs.success = True
            return (result.rowcount or 0) > 0
        except Exception:
            get_logger().warning(
                "db_error", method="update_milestone_progress_db", exc_info=True
            )
            obs.success = False
            return False
