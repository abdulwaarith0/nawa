import uuid
from datetime import UTC, date, datetime

import pytest

from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
from nawa_api.db.cohorts.create_cohort_member_db import create_cohort_member_db
from nawa_api.db.journey.create_milestone_db import create_milestone_db
from nawa_api.db.journey.create_milestone_progress_db import create_milestone_progress_db
from nawa_api.db.journey.delete_milestone_db import delete_milestone_db
from nawa_api.db.journey.get_cohort_board_db import get_cohort_board_db
from nawa_api.db.journey.get_member_timeline_db import get_member_timeline_db
from nawa_api.db.journey.get_milestone_db import get_milestone_db
from nawa_api.db.journey.get_milestone_progress_db import get_milestone_progress_db
from nawa_api.db.journey.instantiate_cohort_milestones_db import (
    instantiate_cohort_milestones_db,
)
from nawa_api.db.journey.list_at_risk_progress_db import list_at_risk_progress_db
from nawa_api.db.journey.list_milestone_progress_db import list_milestone_progress_db
from nawa_api.db.journey.list_milestone_templates_db import list_milestone_templates_db
from nawa_api.db.journey.list_milestones_db import list_milestones_db
from nawa_api.db.journey.update_milestone_db import update_milestone_db
from nawa_api.db.journey.update_milestone_progress_db import update_milestone_progress_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db


async def _program(session):
    return await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="accelerator", name_en="P", session=session
    )


async def _cycle(session, *, program_id):
    return await create_program_cycle_db(
        program_id=program_id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=session
    )


async def _user(session):
    return await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"u{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="User",
        session=session,
    )


async def _cohort(session, *, cycle_id, starts_at=None):
    manager = await _user(session)
    return await create_cohort_db(
        cycle_id=cycle_id,
        program_manager_user_id=manager.id,
        starts_at=starts_at or datetime(2026, 1, 1, tzinfo=UTC),
        name_en="Cohort",
        session=session,
    )


async def _profile(session):
    user = await _user(session)
    return await create_founder_profile_db(
        user_id=user.id, handle=f"h-{uuid.uuid4().hex[:8]}", display_name_en="F", session=session
    )


async def _member(session, *, cohort_id):
    profile = await _profile(session)
    return await create_cohort_member_db(
        cohort_id=cohort_id, profile_id=profile.id, session=session
    )


async def _template(session, *, program_id, cycle_id=None, sequence=1, due_offset_days=7):
    return await create_milestone_db(
        program_id=program_id,
        program_cycle_id=cycle_id,
        scope="template",
        sequence=sequence,
        title_en=f"Template {sequence}",
        due_offset_days=due_offset_days,
        session=session,
    )


@pytest.mark.asyncio
async def test_create_and_get_milestone(db_session):
    program = await _program(db_session)
    row = await create_milestone_db(
        program_id=program.id, scope="template", sequence=1, title_en="M1", session=db_session
    )
    assert row is not None
    fetched = await get_milestone_db(milestone_id=row.id, session=db_session)
    assert fetched is not None
    assert fetched.title_en == "M1"


@pytest.mark.asyncio
async def test_create_milestone_stores_description(db_session):
    program = await _program(db_session)
    row = await create_milestone_db(
        program_id=program.id,
        scope="template",
        sequence=1,
        title_en="M1",
        description_ar="وصف",
        description_en="Desc",
        session=db_session,
    )
    fetched = await get_milestone_db(milestone_id=row.id, session=db_session)
    assert fetched.description_ar == "وصف"
    assert fetched.description_en == "Desc"


@pytest.mark.asyncio
async def test_get_milestone_missing_returns_none(db_session):
    assert await get_milestone_db(milestone_id=uuid.uuid4(), session=db_session) is None


@pytest.mark.asyncio
async def test_list_milestones_filters_by_cohort_and_scope(db_session):
    program = await _program(db_session)
    cycle = await _cycle(db_session, program_id=program.id)
    cohort = await _cohort(db_session, cycle_id=cycle.id)
    template = await _template(db_session, program_id=program.id, sequence=1)
    cohort_row = await create_milestone_db(
        program_id=program.id,
        cohort_id=cohort.id,
        template_id=template.id,
        scope="cohort",
        sequence=1,
        title_en="M1",
        session=db_session,
    )

    only_cohort = await list_milestones_db(cohort_id=cohort.id, session=db_session)
    assert [m.id for m in only_cohort] == [cohort_row.id]

    only_templates = await list_milestones_db(scope="template", session=db_session)
    assert template.id in {m.id for m in only_templates}
    assert cohort_row.id not in {m.id for m in only_templates}


@pytest.mark.asyncio
async def test_list_milestone_templates_orders_by_sequence_and_filters_program(db_session):
    program = await _program(db_session)
    other_program = await _program(db_session)
    t2 = await _template(db_session, program_id=program.id, sequence=2)
    t1 = await _template(db_session, program_id=program.id, sequence=1)
    await _template(db_session, program_id=other_program.id, sequence=1)

    rows = await list_milestone_templates_db(program_id=program.id, session=db_session)
    assert [r.id for r in rows] == [t1.id, t2.id]


@pytest.mark.asyncio
async def test_list_milestone_templates_filters_by_cycle(db_session):
    program = await _program(db_session)
    cycle = await _cycle(db_session, program_id=program.id)
    other_cycle = await _cycle(db_session, program_id=program.id)
    cycle_scoped = await create_milestone_db(
        program_id=program.id, program_cycle_id=cycle.id, scope="template", sequence=1,
        title_en="Cycle-scoped", session=db_session,
    )
    await create_milestone_db(
        program_id=program.id, program_cycle_id=other_cycle.id, scope="template", sequence=2,
        title_en="Other cycle", session=db_session,
    )

    rows = await list_milestone_templates_db(
        program_id=program.id, program_cycle_id=cycle.id, session=db_session
    )
    assert [r.id for r in rows] == [cycle_scoped.id]


@pytest.mark.asyncio
async def test_update_milestone_patches_allowed_fields_only(db_session):
    program = await _program(db_session)
    row = await create_milestone_db(
        program_id=program.id, scope="template", sequence=1, title_en="Old", session=db_session
    )

    ok = await update_milestone_db(
        milestone_id=row.id,
        patch={"title_en": "New", "program_id": uuid.uuid4()},  # program_id must be ignored
        session=db_session,
    )
    assert ok is True
    fetched = await get_milestone_db(milestone_id=row.id, session=db_session)
    assert fetched.title_en == "New"
    assert fetched.program_id == program.id


@pytest.mark.asyncio
async def test_update_milestone_empty_patch_returns_false(db_session):
    program = await _program(db_session)
    row = await create_milestone_db(
        program_id=program.id, scope="template", sequence=1, title_en="Old", session=db_session
    )
    assert await update_milestone_db(milestone_id=row.id, patch={}, session=db_session) is False


@pytest.mark.asyncio
async def test_update_milestone_missing_id_returns_false(db_session):
    ok = await update_milestone_db(
        milestone_id=uuid.uuid4(), patch={"title_en": "X"}, session=db_session
    )
    assert ok is False


@pytest.mark.asyncio
async def test_delete_milestone_removes_row_then_no_ops(db_session):
    program = await _program(db_session)
    row = await create_milestone_db(
        program_id=program.id, scope="template", sequence=1, title_en="M", session=db_session
    )
    assert await delete_milestone_db(milestone_id=row.id, session=db_session) is True
    assert await get_milestone_db(milestone_id=row.id, session=db_session) is None
    assert await delete_milestone_db(milestone_id=row.id, session=db_session) is False


@pytest.mark.asyncio
async def test_create_and_get_milestone_progress(db_session):
    program = await _program(db_session)
    cycle = await _cycle(db_session, program_id=program.id)
    cohort = await _cohort(db_session, cycle_id=cycle.id)
    member = await _member(db_session, cohort_id=cohort.id)
    milestone = await create_milestone_db(
        program_id=program.id,
        cohort_id=cohort.id,
        scope="cohort",
        sequence=1,
        title_en="M",
        session=db_session,
    )

    row = await create_milestone_progress_db(
        milestone_id=milestone.id,
        cohort_member_id=member.id,
        founder_profile_id=member.profile_id,
        session=db_session,
    )
    assert row is not None
    assert row.status == "not_started"
    fetched = await get_milestone_progress_db(progress_id=row.id, session=db_session)
    assert fetched.id == row.id


@pytest.mark.asyncio
async def test_get_milestone_progress_missing_returns_none(db_session):
    assert await get_milestone_progress_db(progress_id=uuid.uuid4(), session=db_session) is None


@pytest.mark.asyncio
async def test_list_milestone_progress_filters(db_session):
    program = await _program(db_session)
    cycle = await _cycle(db_session, program_id=program.id)
    cohort = await _cohort(db_session, cycle_id=cycle.id)
    member_a = await _member(db_session, cohort_id=cohort.id)
    member_b = await _member(db_session, cohort_id=cohort.id)
    milestone = await create_milestone_db(
        program_id=program.id,
        cohort_id=cohort.id,
        scope="cohort",
        sequence=1,
        title_en="M",
        session=db_session,
    )
    progress_a = await create_milestone_progress_db(
        milestone_id=milestone.id,
        cohort_member_id=member_a.id,
        founder_profile_id=member_a.profile_id,
        session=db_session,
    )
    await create_milestone_progress_db(
        milestone_id=milestone.id,
        cohort_member_id=member_b.id,
        founder_profile_id=member_b.profile_id,
        session=db_session,
    )

    by_profile = await list_milestone_progress_db(
        founder_profile_id=member_a.profile_id, session=db_session
    )
    assert [r.id for r in by_profile] == [progress_a.id]

    by_member = await list_milestone_progress_db(
        cohort_member_id=member_a.id, session=db_session
    )
    assert [r.id for r in by_member] == [progress_a.id]


@pytest.mark.asyncio
async def test_update_milestone_progress_patches_and_stamps_updater(db_session):
    program = await _program(db_session)
    cycle = await _cycle(db_session, program_id=program.id)
    cohort = await _cohort(db_session, cycle_id=cycle.id)
    member = await _member(db_session, cohort_id=cohort.id)
    milestone = await create_milestone_db(
        program_id=program.id,
        cohort_id=cohort.id,
        scope="cohort",
        sequence=1,
        title_en="M",
        session=db_session,
    )
    progress = await create_milestone_progress_db(
        milestone_id=milestone.id,
        cohort_member_id=member.id,
        founder_profile_id=member.profile_id,
        session=db_session,
    )
    updater = await _user(db_session)

    ok = await update_milestone_progress_db(
        progress_id=progress.id,
        patch={"status": "in_progress", "evidence_links": [{"url": "https://x", "label": "x"}]},
        updated_by_user_id=updater.id,
        session=db_session,
    )
    assert ok is True
    fetched = await get_milestone_progress_db(progress_id=progress.id, session=db_session)
    assert fetched.status == "in_progress"
    assert fetched.evidence_links == [{"url": "https://x", "label": "x"}]
    assert fetched.updated_by_user_id == updater.id


@pytest.mark.asyncio
async def test_update_milestone_progress_missing_id_returns_false(db_session):
    updater = await _user(db_session)
    ok = await update_milestone_progress_db(
        progress_id=uuid.uuid4(),
        patch={"status": "in_progress"},
        updated_by_user_id=updater.id,
        session=db_session,
    )
    assert ok is False


@pytest.mark.asyncio
async def test_instantiate_cohort_milestones_creates_rows_and_computes_due_date(db_session):
    program = await _program(db_session)
    cycle = await _cycle(db_session, program_id=program.id)
    starts_at = datetime(2026, 3, 1, tzinfo=UTC)
    cohort = await _cohort(db_session, cycle_id=cycle.id, starts_at=starts_at)
    await _template(db_session, program_id=program.id, sequence=1, due_offset_days=7)
    await _template(db_session, program_id=program.id, sequence=2, due_offset_days=14)
    member = await _member(db_session, cohort_id=cohort.id)

    result = await instantiate_cohort_milestones_db(cohort_id=cohort.id, session=db_session)
    assert result == {"milestones_created": 2, "progress_created": 2}

    cohort_milestones = await list_milestones_db(cohort_id=cohort.id, session=db_session)
    by_sequence = {m.sequence: m for m in cohort_milestones}
    assert by_sequence[1].due_date == date(2026, 3, 8)
    assert by_sequence[2].due_date == date(2026, 3, 15)

    progress_rows = await list_milestone_progress_db(
        cohort_member_id=member.id, session=db_session
    )
    assert len(progress_rows) == 2
    assert all(p.status == "not_started" for p in progress_rows)


@pytest.mark.asyncio
async def test_instantiate_cohort_milestones_is_idempotent(db_session):
    program = await _program(db_session)
    cycle = await _cycle(db_session, program_id=program.id)
    cohort = await _cohort(db_session, cycle_id=cycle.id)
    await _template(db_session, program_id=program.id, sequence=1)
    await _member(db_session, cohort_id=cohort.id)

    first = await instantiate_cohort_milestones_db(cohort_id=cohort.id, session=db_session)
    second = await instantiate_cohort_milestones_db(cohort_id=cohort.id, session=db_session)

    assert first == {"milestones_created": 1, "progress_created": 1}
    assert second == {"milestones_created": 0, "progress_created": 0}
    assert len(await list_milestones_db(cohort_id=cohort.id, session=db_session)) == 1


@pytest.mark.asyncio
async def test_instantiate_cohort_milestones_fills_gap_for_late_joiner(db_session):
    program = await _program(db_session)
    cycle = await _cycle(db_session, program_id=program.id)
    cohort = await _cohort(db_session, cycle_id=cycle.id)
    await _template(db_session, program_id=program.id, sequence=1)
    await instantiate_cohort_milestones_db(cohort_id=cohort.id, session=db_session)

    late_member = await _member(db_session, cohort_id=cohort.id)
    result = await instantiate_cohort_milestones_db(cohort_id=cohort.id, session=db_session)

    assert result == {"milestones_created": 0, "progress_created": 1}
    progress_rows = await list_milestone_progress_db(
        cohort_member_id=late_member.id, session=db_session
    )
    assert len(progress_rows) == 1


@pytest.mark.asyncio
async def test_instantiate_cohort_milestones_missing_cohort_returns_empty(db_session):
    result = await instantiate_cohort_milestones_db(cohort_id=uuid.uuid4(), session=db_session)
    assert result == {"milestones_created": 0, "progress_created": 0}


@pytest.mark.asyncio
async def test_get_cohort_board_shape(db_session):
    program = await _program(db_session)
    cycle = await _cycle(db_session, program_id=program.id)
    cohort = await _cohort(db_session, cycle_id=cycle.id)
    await _template(db_session, program_id=program.id, sequence=1)
    await _member(db_session, cohort_id=cohort.id)
    await instantiate_cohort_milestones_db(cohort_id=cohort.id, session=db_session)

    board = await get_cohort_board_db(cohort_id=cohort.id, session=db_session)
    assert len(board["milestones"]) == 1
    assert len(board["members"]) == 1
    assert len(board["progress"]) == 1


@pytest.mark.asyncio
async def test_get_cohort_board_missing_cohort_returns_empty_shape(db_session):
    board = await get_cohort_board_db(cohort_id=uuid.uuid4(), session=db_session)
    assert board == {"milestones": [], "members": [], "progress": []}


@pytest.mark.asyncio
async def test_get_member_timeline_shape(db_session):
    program = await _program(db_session)
    cycle = await _cycle(db_session, program_id=program.id)
    cohort = await _cohort(db_session, cycle_id=cycle.id)
    await _template(db_session, program_id=program.id, sequence=1)
    member = await _member(db_session, cohort_id=cohort.id)
    await instantiate_cohort_milestones_db(cohort_id=cohort.id, session=db_session)

    timeline = await get_member_timeline_db(
        founder_profile_id=member.profile_id, cohort_id=cohort.id, session=db_session
    )
    assert len(timeline["milestones"]) == 1
    assert len(timeline["progress"]) == 1


@pytest.mark.asyncio
async def test_list_at_risk_progress_includes_blocked_and_overdue_excludes_done(db_session):
    program = await _program(db_session)
    cycle = await _cycle(db_session, program_id=program.id)
    cohort = await _cohort(
        db_session, cycle_id=cycle.id, starts_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    member = await _member(db_session, cohort_id=cohort.id)

    overdue_milestone = await create_milestone_db(
        program_id=program.id,
        cohort_id=cohort.id,
        scope="cohort",
        sequence=1,
        title_en="Overdue",
        due_date=date(2026, 1, 1),
        session=db_session,
    )
    done_overdue_milestone = await create_milestone_db(
        program_id=program.id,
        cohort_id=cohort.id,
        scope="cohort",
        sequence=2,
        title_en="Done",
        due_date=date(2026, 1, 1),
        session=db_session,
    )
    future_milestone = await create_milestone_db(
        program_id=program.id,
        cohort_id=cohort.id,
        scope="cohort",
        sequence=3,
        title_en="Future",
        due_date=date(2099, 1, 1),
        session=db_session,
    )

    overdue_progress = await create_milestone_progress_db(
        milestone_id=overdue_milestone.id,
        cohort_member_id=member.id,
        founder_profile_id=member.profile_id,
        status="in_progress",
        session=db_session,
    )
    await create_milestone_progress_db(
        milestone_id=done_overdue_milestone.id,
        cohort_member_id=member.id,
        founder_profile_id=member.profile_id,
        status="done",
        session=db_session,
    )
    blocked_progress = await create_milestone_progress_db(
        milestone_id=future_milestone.id,
        cohort_member_id=member.id,
        founder_profile_id=member.profile_id,
        status="blocked",
        session=db_session,
    )

    at_risk = await list_at_risk_progress_db(
        cohort_id=cohort.id, as_of=date(2026, 6, 1), session=db_session
    )
    at_risk_ids = {progress.id for progress, _milestone in at_risk}
    assert at_risk_ids == {overdue_progress.id, blocked_progress.id}
