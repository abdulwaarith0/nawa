"""Fill-gaps instantiation: copies every template of the cohort's
program/cycle into scope='cohort' rows, then creates a not_started
milestone_progress row for every active cohort member. Idempotent — ON
CONFLICT DO NOTHING against the two partial/full unique indexes means a
re-run (a template added later, a member who joins late) only fills gaps,
never duplicates (07-journey-copilot.md §2.1)."""

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import Milestone, MilestoneProgress
from nawa_api.models.programs import Cohort, CohortMember, ProgramCycle
from nawa_api.utils.logger import get_logger

_EMPTY = {"milestones_created": 0, "progress_created": 0}


async def instantiate_cohort_milestones_db(
    *, cohort_id: uuid.UUID, session: AsyncSession | None = None
) -> dict:
    with observe_db(
        operation="write", table="milestones", method="instantiate_cohort_milestones_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                cohort = (
                    await s.execute(select(Cohort).where(Cohort.id == cohort_id))
                ).scalar_one_or_none()
                if cohort is None:
                    obs.success = False
                    return _EMPTY
                cycle = (
                    await s.execute(
                        select(ProgramCycle).where(ProgramCycle.id == cohort.cycle_id)
                    )
                ).scalar_one_or_none()
                if cycle is None:
                    obs.success = False
                    return _EMPTY

                templates = (
                    (
                        await s.execute(
                            select(Milestone).where(
                                Milestone.program_id == cycle.program_id,
                                Milestone.scope == "template",
                                (Milestone.program_cycle_id == cycle.id)
                                | (Milestone.program_cycle_id.is_(None)),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                milestones_created = 0
                for template in templates:
                    due_date = (
                        cohort.starts_at.date() + timedelta(days=template.due_offset_days)
                        if template.due_offset_days is not None
                        else None
                    )
                    stmt = (
                        insert(Milestone)
                        .values(
                            program_id=template.program_id,
                            program_cycle_id=template.program_cycle_id,
                            cohort_id=cohort_id,
                            template_id=template.id,
                            scope="cohort",
                            sequence=template.sequence,
                            title_ar=template.title_ar,
                            title_en=template.title_en,
                            description_ar=template.description_ar,
                            description_en=template.description_en,
                            due_offset_days=template.due_offset_days,
                            due_date=due_date,
                            evidence_required=template.evidence_required,
                            config=template.config,
                        )
                        .on_conflict_do_nothing(
                            index_elements=[Milestone.cohort_id, Milestone.template_id],
                            index_where=Milestone.template_id.isnot(None),
                        )
                        .returning(Milestone.id)
                    )
                    if (await s.execute(stmt)).first() is not None:
                        milestones_created += 1

                cohort_milestones = (
                    (
                        await s.execute(
                            select(Milestone.id).where(
                                Milestone.cohort_id == cohort_id, Milestone.scope == "cohort"
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                members = (
                    (
                        await s.execute(
                            select(CohortMember).where(
                                CohortMember.cohort_id == cohort_id,
                                CohortMember.status == "active",
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                progress_created = 0
                for milestone_id in cohort_milestones:
                    for member in members:
                        stmt = (
                            insert(MilestoneProgress)
                            .values(
                                milestone_id=milestone_id,
                                cohort_member_id=member.id,
                                founder_profile_id=member.profile_id,
                                status="not_started",
                            )
                            .on_conflict_do_nothing(
                                index_elements=[
                                    MilestoneProgress.milestone_id,
                                    MilestoneProgress.cohort_member_id,
                                ]
                            )
                            .returning(MilestoneProgress.id)
                        )
                        if (await s.execute(stmt)).first() is not None:
                            progress_created += 1
            obs.success = True
            return {
                "milestones_created": milestones_created,
                "progress_created": progress_created,
            }
        except Exception:
            get_logger().warning(
                "db_error", method="instantiate_cohort_milestones_db", exc_info=True
            )
            obs.success = False
            return _EMPTY
