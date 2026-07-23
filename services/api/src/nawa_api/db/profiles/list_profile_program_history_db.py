import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.programs import Cohort, CohortMember, Program, ProgramCycle
from nawa_api.utils.logger import get_logger


async def list_profile_program_history_db(
    *, profile_id: uuid.UUID, session: AsyncSession | None = None
) -> list[dict]:
    """Program history is DERIVED, never stored: cohort_members -> cohorts ->
    program_cycles -> programs, ordered by cohorts.starts_at (newest first)."""
    with observe_db(
        operation="read", table="cohort_members", method="list_profile_program_history_db"
    ) as obs:
        try:
            stmt = (
                select(CohortMember, Cohort, ProgramCycle, Program)
                .join(Cohort, Cohort.id == CohortMember.cohort_id)
                .join(ProgramCycle, ProgramCycle.id == Cohort.cycle_id)
                .join(Program, Program.id == ProgramCycle.program_id)
                .where(CohortMember.profile_id == profile_id)
                .order_by(Cohort.starts_at.desc())
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).all()
            obs.success = True
            return [
                {
                    "program": program,
                    "cycle": cycle,
                    "cohort": cohort,
                    "membership": member,
                }
                for member, cohort, cycle, program in rows
            ]
        except Exception:
            get_logger().warning(
                "db_error", method="list_profile_program_history_db", exc_info=True
            )
            obs.success = False
            return []
