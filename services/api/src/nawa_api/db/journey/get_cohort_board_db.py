"""One round trip's worth of raw rows for the program-manager board grid
(06-intake-copilot.md's list_shortlist_db/_build_items split, mirrored here):
this returns milestones × active members × progress rows; the SERVICE layer
(services/journey/get_cohort_board.py) assembles the grid, since building a
nested structure from three flat row sets is business shape, not SQL.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import Milestone, MilestoneProgress
from nawa_api.models.profiles import FounderProfile
from nawa_api.models.programs import CohortMember
from nawa_api.utils.logger import get_logger


async def get_cohort_board_db(
    *, cohort_id: uuid.UUID, session: AsyncSession | None = None
) -> dict:
    empty = {"milestones": [], "members": [], "progress": []}
    with observe_db(
        operation="read", table="milestone_progress", method="get_cohort_board_db"
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
                members = (
                    (
                        await s.execute(
                            select(CohortMember, FounderProfile)
                            .join(FounderProfile, FounderProfile.id == CohortMember.profile_id)
                            .where(
                                CohortMember.cohort_id == cohort_id,
                                CohortMember.status == "active",
                            )
                        )
                    )
                    .all()
                )
                member_ids = [m.id for m, _p in members]
                progress = (
                    (
                        await s.execute(
                            select(MilestoneProgress).where(
                                MilestoneProgress.cohort_member_id.in_(member_ids)
                            )
                        )
                    )
                    .scalars()
                    .all()
                    if member_ids
                    else []
                )
            obs.success = True
            return {"milestones": list(milestones), "members": members, "progress": list(progress)}
        except Exception:
            get_logger().warning("db_error", method="get_cohort_board_db", exc_info=True)
            obs.success = False
            return empty
