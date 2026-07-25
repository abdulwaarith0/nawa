"""Generic Milestone patch — shared by the template-management service and
the cohort-milestone-management service (both patch the same columns on the
same table; 07-journey-copilot.md names them as two db functions, but they'd
be byte-identical SQL, so the split lives at the service layer's validation
instead, per this codebase's tolerance for small duplication avoidance over
premature abstraction — see services/journey/update_milestone_template.py /
update_cohort_milestone.py)."""

import uuid
from datetime import date

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import Milestone
from nawa_api.utils.logger import get_logger

_PATCHABLE_FIELDS = frozenset(
    {
        "title_ar",
        "title_en",
        "description_ar",
        "description_en",
        "sequence",
        "due_offset_days",
        "due_date",
        "evidence_required",
        "config",
    }
)


async def update_milestone_db(
    *,
    milestone_id: uuid.UUID,
    patch: dict[str, str | int | bool | dict | date | None],
    session: AsyncSession | None = None,
) -> bool:
    values = {k: v for k, v in patch.items() if k in _PATCHABLE_FIELDS}
    if not values:
        return False
    with observe_db(operation="write", table="milestones", method="update_milestone_db") as obs:
        try:
            stmt = update(Milestone).where(Milestone.id == milestone_id).values(**values)
            async with use_session(session) as s:
                result = await s.execute(stmt)
            obs.success = True
            return (result.rowcount or 0) > 0
        except Exception:
            get_logger().warning("db_error", method="update_milestone_db", exc_info=True)
            obs.success = False
            return False
