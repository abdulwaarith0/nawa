"""Directory read (08-community-hub.md §3): every visible member profile,
text-searched over `search_tsv` and filtered by domains/skills/sector/
country/program/stage/mentor-eligibility. Visibility is never negotiable
here — `is_public` AND the linked `users.is_active` gate every row, always.

Program membership is derived, never stored: reuses the exact
cohort_members -> cohorts -> program_cycles -> programs join chain
`list_profile_program_history_db` uses, correlated as an EXISTS so a
profile with several memberships in the same program still yields one row.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.profiles.program_history_join import join_cohort_membership_chain
from nawa_api.db.utils import clamp_pagination, use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import User
from nawa_api.models.profiles import FounderProfile
from nawa_api.models.programs import CohortMember, ProgramCycle
from nawa_api.utils.logger import get_logger


async def list_directory_db(
    *,
    q: str | None = None,
    domains: list[str] | None = None,
    skills: list[str] | None = None,
    sector: str | None = None,
    country: str | None = None,
    program_id: uuid.UUID | None = None,
    stage: str | None = None,
    mentors: bool | None = None,
    limit: int | None = None,
    offset: int | None = None,
    session: AsyncSession | None = None,
) -> list[FounderProfile]:
    clamped_limit, clamped_offset = clamp_pagination(limit=limit, offset=offset)
    with observe_db(operation="read", table="founder_profiles", method="list_directory_db") as obs:
        try:
            stmt = (
                select(FounderProfile)
                .join(User, User.id == FounderProfile.user_id)
                .where(FounderProfile.is_public.is_(True), User.is_active.is_(True))
            )

            tsquery = None
            if q:
                tsquery = func.websearch_to_tsquery("simple", q)
                stmt = stmt.where(FounderProfile.search_tsv.op("@@")(tsquery))
            if domains:
                stmt = stmt.where(FounderProfile.domains.overlap(domains))
            if skills:
                stmt = stmt.where(FounderProfile.skills.overlap(skills))
            if sector is not None:
                stmt = stmt.where(FounderProfile.sector == sector)
            if country is not None:
                stmt = stmt.where(FounderProfile.country == country)
            if stage is not None:
                stmt = stmt.where(FounderProfile.stage == stage)
            if mentors:
                stmt = stmt.where(FounderProfile.is_mentor_eligible.is_(True))
            if program_id is not None:
                history_exists = join_cohort_membership_chain(
                    select(CohortMember.id)
                ).where(
                    CohortMember.profile_id == FounderProfile.id,
                    ProgramCycle.program_id == program_id,
                )
                stmt = stmt.where(history_exists.exists())

            if tsquery is not None:
                stmt = stmt.order_by(func.ts_rank(FounderProfile.search_tsv, tsquery).desc())
            else:
                # canonical directory sort (recently_active): the exact
                # column order `ix_founder_profiles_directory` was built for.
                stmt = stmt.order_by(FounderProfile.is_public.desc(), FounderProfile.updated_at.desc())

            stmt = stmt.limit(clamped_limit).offset(clamped_offset)
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_directory_db", exc_info=True)
            obs.success = False
            return []
