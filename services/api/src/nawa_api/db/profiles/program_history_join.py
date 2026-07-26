"""Shared join chain: cohort_members -> cohorts -> program_cycles -> programs.

Program history is DERIVED, never stored (03-data-spine.md). Two call sites
need this exact chain: `list_profile_program_history_db` (a profile's full
history, newest first) and the community directory's `program_id` filter
(an EXISTS correlation against `founder_profiles.id`) — factored here so
there is exactly one join, not two copies drifting apart.
"""

from __future__ import annotations

from sqlalchemy import Select

from nawa_api.models.programs import Cohort, CohortMember, Program, ProgramCycle


def join_cohort_membership_chain(stmt: Select) -> Select:
    """Joins `Cohort`, `ProgramCycle`, and `Program` onto a statement that
    already selects from/references `CohortMember` (e.g. `select(CohortMember)`
    or `select(CohortMember.id)`)."""
    return (
        stmt.join(Cohort, Cohort.id == CohortMember.cohort_id)
        .join(ProgramCycle, ProgramCycle.id == Cohort.cycle_id)
        .join(Program, Program.id == ProgramCycle.program_id)
    )
