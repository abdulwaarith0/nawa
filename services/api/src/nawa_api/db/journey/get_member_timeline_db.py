"""Founder's own timeline: every instantiated milestone for the cohort, plus
this member's own progress row per milestone (a left-join shape, assembled
in Python since asyncpg/SQLAlchemy outer-join rows are awkward to type
cleanly — the service layer pairs them by milestone_id).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import Milestone, MilestoneProgress
from nawa_api.utils.logger import get_logger


async def get_member_timeline_db(
    *, founder_profile_id: uuid.UUID, cohort_id: uuid.UUID, session: AsyncSession | None = None
) -> dict:
    empty = {"milestones": [], "progress": []}
    with observe_db(
        operation="read", table="milestone_progress", method="get_member_timeline_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                milestones = (
                    (
                        await s.execute(
                            select(Milestone)
                            .where(Milestone.cohort_id == cohort_id, Milestone.scope == "cohort")
                            .order_by(Milestone.sequence)
                        )
                    )
                    .scalars()
                    .all()
                )
                progress = (
                    (
                        await s.execute(
                            select(MilestoneProgress).where(
                                MilestoneProgress.founder_profile_id == founder_profile_id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
            obs.success = True
            return {"milestones": list(milestones), "progress": list(progress)}
        except Exception:
            get_logger().warning("db_error", method="get_member_timeline_db", exc_info=True)
            obs.success = False
            return empty
