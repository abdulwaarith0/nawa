"""Overdue-or-blocked progress rows for a cohort (07-journey-copilot.md
§2.2/§4.2): the board's overdue-cell flag and the digest's at-risk section
both read this. 'Overdue' = past the milestone's due_date and not yet
done/waived; 'blocked' is a status regardless of due date. Returns
(MilestoneProgress, Milestone) pairs — the service layer derives the
machine-readable reason (`overdue:<milestone_id>` / `blocked:<progress_id>`)."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import Milestone, MilestoneProgress
from nawa_api.utils.logger import get_logger

_NOT_AT_RISK_STATUSES = ("done", "waived")


async def list_at_risk_progress_db(
    *, cohort_id: uuid.UUID, as_of: date, session: AsyncSession | None = None
) -> list[tuple[MilestoneProgress, Milestone]]:
    with observe_db(
        operation="read", table="milestone_progress", method="list_at_risk_progress_db"
    ) as obs:
        try:
            stmt = (
                select(MilestoneProgress, Milestone)
                .join(Milestone, Milestone.id == MilestoneProgress.milestone_id)
                .where(
                    Milestone.cohort_id == cohort_id,
                    Milestone.scope == "cohort",
                    MilestoneProgress.status.notin_(_NOT_AT_RISK_STATUSES),
                )
                .where(
                    (MilestoneProgress.status == "blocked")
                    | ((Milestone.due_date.isnot(None)) & (Milestone.due_date < as_of))
                )
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).all()
            obs.success = True
            return [(progress, milestone) for progress, milestone in rows]
        except Exception:
            get_logger().warning("db_error", method="list_at_risk_progress_db", exc_info=True)
            obs.success = False
            return []
