import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.programs import CohortMember
from nawa_api.utils.logger import get_logger


async def upsert_cohort_member_db(
    *,
    cohort_id: uuid.UUID,
    profile_id: uuid.UUID,
    role: str = "participant",
    status: str = "active",
    session: AsyncSession | None = None,
) -> bool:
    """Idempotent on the unique (cohort_id, profile_id) pair — re-accepting an
    already-accepted applicant is a no-op, not an error (06-intake-copilot.md
    §6.2). ON CONFLICT DO NOTHING: an existing membership's role/status is
    never overwritten by a repeat acceptance."""
    with observe_db(
        operation="write", table="cohort_members", method="upsert_cohort_member_db"
    ) as obs:
        try:
            stmt = insert(CohortMember).values(
                cohort_id=cohort_id, profile_id=profile_id, role=role, status=status
            )
            stmt = stmt.on_conflict_do_nothing(
                index_elements=[CohortMember.cohort_id, CohortMember.profile_id]
            )
            async with use_session(session) as s:
                await s.execute(stmt)
            obs.success = True
            return True
        except Exception:
            get_logger().warning("db_error", method="upsert_cohort_member_db", exc_info=True)
            obs.success = False
            return False
