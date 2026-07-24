from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import clamp_pagination, use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Application
from nawa_api.utils.logger import get_logger


async def list_applications_by_email_db(
    *,
    applicant_email: str,
    limit: int | None = None,
    session: AsyncSession | None = None,
) -> list[Application]:
    """Exact-email candidate generation for dedup (06-intake-copilot.md §4) —
    deliberately UNSCOPED by cycle: a resubmission across seasons is the point.
    `applicant_email` is CITEXT, so equality is already case-insensitive."""
    clamped_limit, _ = clamp_pagination(limit=limit, offset=None)
    with observe_db(
        operation="read", table="applications", method="list_applications_by_email_db"
    ) as obs:
        try:
            stmt = (
                select(Application)
                .where(Application.applicant_email == applicant_email)
                .limit(clamped_limit)
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning(
                "db_error", method="list_applications_by_email_db", exc_info=True
            )
            obs.success = False
            return []
