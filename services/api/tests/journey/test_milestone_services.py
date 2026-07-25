import uuid
from datetime import UTC, date, datetime

import pytest_asyncio

from nawa_api.contracts.errors import ApiError
from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
from nawa_api.db.cohorts.create_cohort_member_db import create_cohort_member_db
from nawa_api.db.journey.create_milestone_db import create_milestone_db
from nawa_api.db.journey.create_milestone_progress_db import create_milestone_progress_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.runtime.redis import get_redis
from nawa_api.services.journey import create_milestone_template as create_milestone_template_mod
from nawa_api.services.journey import delete_milestone_template as delete_milestone_template_mod
from nawa_api.services.journey import get_cohort_board as get_cohort_board_mod
from nawa_api.services.journey import get_member_timeline as get_member_timeline_mod
from nawa_api.services.journey import list_at_risk as list_at_risk_mod
from nawa_api.services.journey import list_cohort_milestones as list_cohort_milestones_mod
from nawa_api.services.journey import list_milestone_templates as list_milestone_templates_mod
from nawa_api.services.journey import update_cohort_milestone as update_cohort_milestone_mod
from nawa_api.services.journey import update_milestone_template as update_milestone_template_mod
from nawa_api.services.journey.create_milestone_template import create_milestone_template
from nawa_api.services.journey.delete_milestone_template import delete_milestone_template
from nawa_api.services.journey.get_cohort_board import get_cohort_board
from nawa_api.services.journey.get_member_timeline import get_member_timeline
from nawa_api.services.journey.instantiate_cohort_milestones import (
    instantiate_cohort_milestones,
)
from nawa_api.services.journey.list_at_risk import list_at_risk
from nawa_api.services.journey.list_cohort_milestones import list_cohort_milestones
from nawa_api.services.journey.list_milestone_templates import list_milestone_templates
from nawa_api.services.journey.review_milestone_progress import review_milestone_progress
from nawa_api.services.journey.update_cohort_milestone import update_cohort_milestone
from nawa_api.services.journey.update_milestone_progress import update_milestone_progress
from nawa_api.services.journey.update_milestone_template import update_milestone_template


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


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
        starts_at=starts_at or datetime(2020, 1, 1, tzinfo=UTC),
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


async def _template(session, *, program_id, sequence=1, due_offset_days=None):
    return await create_milestone_db(
        program_id=program_id,
        scope="template",
        sequence=sequence,
        title_en=f"T{sequence}",
        due_offset_days=due_offset_days,
        session=session,
    )


# --- list/create/update/delete milestone templates -------------------------------------------


async def test_list_milestone_templates_empty_not_cached(bound):
    program = await _program(bound)
    await bound.commit()
    assert await list_milestone_templates(program_id=program.id) == []
    key = list_milestone_templates_mod.cache_key(program_id=program.id, program_cycle_id=None)
    assert await get_redis().get(key) is None


async def test_create_milestone_template_requires_a_title(bound):
    program = await _program(bound)
    await bound.commit()
    try:
        await create_milestone_template(program_id=program.id, sequence=1)
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 400


async def test_create_then_list_milestone_templates_is_cached_until_invalidated(bound, monkeypatch):
    program = await _program(bound)
    await bound.commit()

    created = await create_milestone_template(
        program_id=program.id, sequence=1, title_en="Kickoff", due_offset_days=7
    )
    assert created["title_en"] == "Kickoff"

    first = await list_milestone_templates(program_id=program.id)
    assert len(first) == 1

    calls = {"n": 0}
    real = list_milestone_templates_mod.list_milestone_templates_db

    async def counting(*args, **kwargs):
        calls["n"] += 1
        return await real(*args, **kwargs)

    monkeypatch.setattr(list_milestone_templates_mod, "list_milestone_templates_db", counting)
    second = await list_milestone_templates(program_id=program.id)
    assert second == first
    assert calls["n"] == 0  # served from cache

    await create_milestone_template(program_id=program.id, sequence=2, title_en="Demo Day")
    monkeypatch.setattr(list_milestone_templates_mod, "list_milestone_templates_db", real)
    third = await list_milestone_templates(program_id=program.id)
    assert len(third) == 2  # cache was invalidated by the second create


async def test_update_milestone_template_rejects_cohort_scoped_row(bound):
    program = await _program(bound)
    cycle = await _cycle(bound, program_id=program.id)
    cohort = await _cohort(bound, cycle_id=cycle.id)
    cohort_row = await create_milestone_db(
        program_id=program.id, cohort_id=cohort.id, scope="cohort", sequence=1, title_en="M",
        session=bound,
    )
    await bound.commit()
    try:
        await update_milestone_template(milestone_id=cohort_row.id, patch={"title_en": "X"})
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 404


async def test_update_milestone_template_patches_fields(bound):
    program = await _program(bound)
    await bound.commit()
    template = await create_milestone_template(program_id=program.id, sequence=1, title_en="Old")
    await bound.commit()
    updated = await update_milestone_template(
        milestone_id=uuid.UUID(template["id"]), patch={"title_en": "New"}
    )
    assert updated["title_en"] == "New"


async def test_delete_milestone_template_rejects_missing_id(bound):
    try:
        await delete_milestone_template(milestone_id=uuid.uuid4())
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 404


async def test_delete_milestone_template_removes_row_and_invalidates(bound):
    program = await _program(bound)
    await bound.commit()
    template = await create_milestone_template(program_id=program.id, sequence=1, title_en="T")
    await list_milestone_templates(program_id=program.id)  # warm the cache

    await delete_milestone_template(milestone_id=uuid.UUID(template["id"]))
    assert await list_milestone_templates(program_id=program.id) == []


# --- instantiation + cohort milestones --------------------------------------------------------


async def test_instantiate_missing_cohort_raises_not_found(bound):
    try:
        await instantiate_cohort_milestones(cohort_id=uuid.uuid4())
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 404


async def test_instantiate_creates_rows_and_is_idempotent(bound):
    program = await _program(bound)
    cycle = await _cycle(bound, program_id=program.id)
    cohort = await _cohort(bound, cycle_id=cycle.id)
    await _template(bound, program_id=program.id, sequence=1, due_offset_days=7)
    await _member(bound, cohort_id=cohort.id)
    await bound.commit()

    first = await instantiate_cohort_milestones(cohort_id=cohort.id)
    second = await instantiate_cohort_milestones(cohort_id=cohort.id)
    assert first == {"milestones_created": 1, "progress_created": 1}
    assert second == {"milestones_created": 0, "progress_created": 0}


async def test_instantiate_invalidates_cohort_milestones_cache(bound):
    program = await _program(bound)
    cycle = await _cycle(bound, program_id=program.id)
    cohort = await _cohort(bound, cycle_id=cycle.id)
    await _template(bound, program_id=program.id, sequence=1)
    await _member(bound, cohort_id=cohort.id)
    await bound.commit()

    assert await list_cohort_milestones(cohort_id=cohort.id) == []  # nothing yet, not cached
    await instantiate_cohort_milestones(cohort_id=cohort.id)
    after = await list_cohort_milestones(cohort_id=cohort.id)
    assert len(after) == 1


async def test_update_cohort_milestone_rejects_template_scoped_row(bound):
    program = await _program(bound)
    template = await _template(bound, program_id=program.id, sequence=1)
    await bound.commit()
    try:
        await update_cohort_milestone(milestone_id=template.id, patch={"title_en": "X"})
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 404


async def test_update_cohort_milestone_patches_and_invalidates_board(bound):
    program = await _program(bound)
    cycle = await _cycle(bound, program_id=program.id)
    cohort = await _cohort(bound, cycle_id=cycle.id)
    await _template(bound, program_id=program.id, sequence=1)
    await _member(bound, cohort_id=cohort.id)
    await bound.commit()
    await instantiate_cohort_milestones(cohort_id=cohort.id)
    milestones = await list_cohort_milestones(cohort_id=cohort.id)
    milestone_id = uuid.UUID(milestones[0]["id"])

    await get_cohort_board(cohort_id=cohort.id)  # warm the board cache
    board_key = get_cohort_board_mod.cache_key(cohort_id=cohort.id)
    assert await get_redis().get(board_key) is not None

    await update_cohort_milestone(milestone_id=milestone_id, patch={"title_en": "Renamed"})
    assert await get_redis().get(board_key) is None  # invalidated

    board = await get_cohort_board(cohort_id=cohort.id)
    assert board["milestones"][0]["title_en"] == "Renamed"


# --- board + timeline -------------------------------------------------------------------------


async def test_get_cohort_board_shape_and_overdue_flag(bound):
    program = await _program(bound)
    cycle = await _cycle(bound, program_id=program.id)
    cohort = await _cohort(bound, cycle_id=cycle.id, starts_at=datetime(2020, 1, 1, tzinfo=UTC))
    member = await _member(bound, cohort_id=cohort.id)
    milestone = await create_milestone_db(
        program_id=program.id, cohort_id=cohort.id, scope="cohort", sequence=1, title_en="M",
        due_date=date(2020, 1, 1), session=bound,
    )
    await create_milestone_progress_db(
        milestone_id=milestone.id, cohort_member_id=member.id,
        founder_profile_id=member.profile_id, status="in_progress", session=bound,
    )
    await bound.commit()

    board = await get_cohort_board(cohort_id=cohort.id)
    assert len(board["milestones"]) == 1
    assert len(board["members"]) == 1
    assert board["cells"][0]["overdue"] is True
    assert board["cells"][0]["status"] == "in_progress"


async def test_get_member_timeline_defaults_missing_progress_to_not_started(bound):
    program = await _program(bound)
    cycle = await _cycle(bound, program_id=program.id)
    cohort = await _cohort(bound, cycle_id=cycle.id)
    member = await _member(bound, cohort_id=cohort.id)
    await create_milestone_db(
        program_id=program.id, cohort_id=cohort.id, scope="cohort", sequence=1, title_en="M",
        session=bound,
    )
    await bound.commit()

    timeline = await get_member_timeline(founder_profile_id=member.profile_id, cohort_id=cohort.id)
    assert len(timeline) == 1
    assert timeline[0]["status"] == "not_started"
    assert timeline[0]["progress_id"] is None


# --- founder progress update -------------------------------------------------------------------


async def _cohort_with_progress(session, *, due_date=None):
    program = await _program(session)
    cycle = await _cycle(session, program_id=program.id)
    cohort = await _cohort(session, cycle_id=cycle.id)
    member = await _member(session, cohort_id=cohort.id)
    milestone = await create_milestone_db(
        program_id=program.id, cohort_id=cohort.id, scope="cohort", sequence=1, title_en="M",
        due_date=due_date, session=session,
    )
    progress = await create_milestone_progress_db(
        milestone_id=milestone.id, cohort_member_id=member.id,
        founder_profile_id=member.profile_id, session=session,
    )
    return cohort, member, milestone, progress


async def test_update_milestone_progress_rejects_manager_only_status(bound):
    _cohort, member, _m, progress = await _cohort_with_progress(bound)
    await bound.commit()
    try:
        await update_milestone_progress(
            progress_id=progress.id, founder_profile_id=member.profile_id,
            updated_by_user_id=member.profile_id, status="done",
        )
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 400


async def test_update_milestone_progress_rejects_skipped_transition(bound):
    _cohort, member, _m, progress = await _cohort_with_progress(bound)
    await bound.commit()
    try:
        await update_milestone_progress(
            progress_id=progress.id, founder_profile_id=member.profile_id,
            updated_by_user_id=member.profile_id, status="submitted",
        )
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 400


async def test_update_milestone_progress_foreign_id_is_404(bound):
    _cohort, _member, _m, progress = await _cohort_with_progress(bound)
    await bound.commit()
    try:
        await update_milestone_progress(
            progress_id=progress.id, founder_profile_id=uuid.uuid4(),
            updated_by_user_id=uuid.uuid4(), status="in_progress",
        )
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 404


async def test_update_milestone_progress_empty_patch_is_400(bound):
    _cohort, member, _m, progress = await _cohort_with_progress(bound)
    await bound.commit()
    try:
        await update_milestone_progress(
            progress_id=progress.id, founder_profile_id=member.profile_id,
            updated_by_user_id=member.profile_id,
        )
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 400


async def test_update_milestone_progress_valid_transition_and_evidence(bound):
    cohort, member, _m, progress = await _cohort_with_progress(bound)
    updater = await _user(bound)
    await bound.commit()

    result = await update_milestone_progress(
        progress_id=progress.id, founder_profile_id=member.profile_id,
        updated_by_user_id=updater.id, status="in_progress",
        evidence_links=[{"url": "https://x", "label": "doc"}],
    )
    assert result["status"] == "in_progress"
    assert result["evidence_links"] == [{"url": "https://x", "label": "doc"}]


async def test_update_milestone_progress_invalidates_board_and_timeline_caches(bound):
    cohort, member, _m, progress = await _cohort_with_progress(bound)
    updater = await _user(bound)
    await bound.commit()

    await get_cohort_board(cohort_id=cohort.id)
    await get_member_timeline(founder_profile_id=member.profile_id, cohort_id=cohort.id)
    board_key = get_cohort_board_mod.cache_key(cohort_id=cohort.id)
    timeline_key = get_member_timeline_mod.cache_key(
        founder_profile_id=member.profile_id, cohort_id=cohort.id
    )
    assert await get_redis().get(board_key) is not None
    assert await get_redis().get(timeline_key) is not None

    await update_milestone_progress(
        progress_id=progress.id, founder_profile_id=member.profile_id,
        updated_by_user_id=updater.id, status="in_progress",
    )
    assert await get_redis().get(board_key) is None
    assert await get_redis().get(timeline_key) is None


# --- manager review ------------------------------------------------------------------------


async def test_review_missing_progress_is_404(bound):
    reviewer = await _user(bound)
    await bound.commit()
    try:
        await review_milestone_progress(
            progress_id=uuid.uuid4(), reviewed_by_user_id=reviewer.id, status="done"
        )
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 404


async def test_review_blocked_requires_a_note(bound):
    _cohort, _member, _m, progress = await _cohort_with_progress(bound)
    reviewer = await _user(bound)
    await bound.commit()
    try:
        await review_milestone_progress(
            progress_id=progress.id, reviewed_by_user_id=reviewer.id, status="blocked"
        )
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 400


async def test_review_not_started_cannot_jump_to_done(bound):
    _cohort, _member, _m, progress = await _cohort_with_progress(bound)
    reviewer = await _user(bound)
    await bound.commit()
    try:
        await review_milestone_progress(
            progress_id=progress.id, reviewed_by_user_id=reviewer.id, status="done"
        )
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 400


async def test_review_submitted_to_done_then_reopen(bound):
    cohort, member, milestone, progress = await _cohort_with_progress(bound)
    reviewer = await _user(bound)
    await bound.commit()
    await update_milestone_progress(
        progress_id=progress.id, founder_profile_id=member.profile_id,
        updated_by_user_id=reviewer.id, status="in_progress",
    )
    await update_milestone_progress(
        progress_id=progress.id, founder_profile_id=member.profile_id,
        updated_by_user_id=reviewer.id, status="submitted",
    )

    accepted = await review_milestone_progress(
        progress_id=progress.id, reviewed_by_user_id=reviewer.id, status="done"
    )
    assert accepted["status"] == "done"
    assert accepted["reviewed_by_user_id"] == str(reviewer.id)

    reopened = await review_milestone_progress(
        progress_id=progress.id, reviewed_by_user_id=reviewer.id, status="submitted"
    )
    assert reopened["status"] == "submitted"


async def test_review_blocked_with_note_from_any_status(bound):
    _cohort, _member, _m, progress = await _cohort_with_progress(bound)
    reviewer = await _user(bound)
    await bound.commit()
    result = await review_milestone_progress(
        progress_id=progress.id, reviewed_by_user_id=reviewer.id, status="blocked",
        note_en="Missing evidence.",
    )
    assert result["status"] == "blocked"
    assert result["note_en"] == "Missing evidence."


# --- at-risk --------------------------------------------------------------------------------


async def test_list_at_risk_includes_overdue_and_blocked_excludes_done(bound):
    program = await _program(bound)
    cycle = await _cycle(bound, program_id=program.id)
    cohort = await _cohort(bound, cycle_id=cycle.id)
    member = await _member(bound, cohort_id=cohort.id)

    overdue_m = await create_milestone_db(
        program_id=program.id, cohort_id=cohort.id, scope="cohort", sequence=1, title_en="Overdue",
        due_date=date(2020, 1, 1), session=bound,
    )
    done_m = await create_milestone_db(
        program_id=program.id, cohort_id=cohort.id, scope="cohort", sequence=2, title_en="Done",
        due_date=date(2020, 1, 1), session=bound,
    )
    future_m = await create_milestone_db(
        program_id=program.id, cohort_id=cohort.id, scope="cohort", sequence=3, title_en="Future",
        due_date=date(2099, 1, 1), session=bound,
    )
    overdue_p = await create_milestone_progress_db(
        milestone_id=overdue_m.id, cohort_member_id=member.id,
        founder_profile_id=member.profile_id, status="in_progress", session=bound,
    )
    await create_milestone_progress_db(
        milestone_id=done_m.id, cohort_member_id=member.id,
        founder_profile_id=member.profile_id, status="done", session=bound,
    )
    blocked_p = await create_milestone_progress_db(
        milestone_id=future_m.id, cohort_member_id=member.id,
        founder_profile_id=member.profile_id, status="blocked", session=bound,
    )
    await bound.commit()

    items = await list_at_risk(cohort_id=cohort.id)
    by_id = {i["progress_id"]: i for i in items}
    assert set(by_id) == {str(overdue_p.id), str(blocked_p.id)}
    assert by_id[str(overdue_p.id)]["reasons"] == [f"overdue:{overdue_m.id}"]
    assert by_id[str(blocked_p.id)]["reasons"] == [f"blocked:{blocked_p.id}"]


async def test_create_milestone_template_db_failure_raises_400(bound, monkeypatch):
    program = await _program(bound)
    await bound.commit()

    async def fails(**_kwargs):
        return None

    monkeypatch.setattr(create_milestone_template_mod, "create_milestone_db", fails)
    try:
        await create_milestone_template(program_id=program.id, sequence=1, title_en="X")
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 400


async def test_update_milestone_template_db_failure_raises_400(bound, monkeypatch):
    program = await _program(bound)
    await bound.commit()
    template = await create_milestone_template(program_id=program.id, sequence=1, title_en="X")

    async def fails(**_kwargs):
        return False

    monkeypatch.setattr(update_milestone_template_mod, "update_milestone_db", fails)
    try:
        await update_milestone_template(
            milestone_id=uuid.UUID(template["id"]), patch={"title_en": "Y"}
        )
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 400


async def test_delete_milestone_template_db_failure_raises_404(bound, monkeypatch):
    program = await _program(bound)
    await bound.commit()
    template = await create_milestone_template(program_id=program.id, sequence=1, title_en="X")

    async def fails(**_kwargs):
        return False

    monkeypatch.setattr(delete_milestone_template_mod, "delete_milestone_db", fails)
    try:
        await delete_milestone_template(milestone_id=uuid.UUID(template["id"]))
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 404


async def test_update_cohort_milestone_db_failure_raises_400(bound, monkeypatch):
    program = await _program(bound)
    cycle = await _cycle(bound, program_id=program.id)
    cohort = await _cohort(bound, cycle_id=cycle.id)
    await _template(bound, program_id=program.id, sequence=1)
    await bound.commit()
    await instantiate_cohort_milestones(cohort_id=cohort.id)
    milestone = (await list_cohort_milestones(cohort_id=cohort.id))[0]

    async def fails(**_kwargs):
        return False

    monkeypatch.setattr(update_cohort_milestone_mod, "update_milestone_db", fails)
    try:
        await update_cohort_milestone(
            milestone_id=uuid.UUID(milestone["id"]), patch={"title_en": "Y"}
        )
        raise AssertionError("expected ApiError")
    except ApiError as exc:
        assert exc.code == 400


async def test_list_cohort_milestones_is_cached_until_invalidated(bound, monkeypatch):
    program = await _program(bound)
    cycle = await _cycle(bound, program_id=program.id)
    cohort = await _cohort(bound, cycle_id=cycle.id)
    await _template(bound, program_id=program.id, sequence=1)
    await bound.commit()
    await instantiate_cohort_milestones(cohort_id=cohort.id)

    first = await list_cohort_milestones(cohort_id=cohort.id)
    calls = {"n": 0}
    real = list_cohort_milestones_mod.list_milestones_db

    async def counting(*args, **kwargs):
        calls["n"] += 1
        return await real(*args, **kwargs)

    monkeypatch.setattr(list_cohort_milestones_mod, "list_milestones_db", counting)
    second = await list_cohort_milestones(cohort_id=cohort.id)
    assert second == first
    assert calls["n"] == 0


async def test_get_cohort_board_is_cached_until_invalidated(bound, monkeypatch):
    program = await _program(bound)
    cycle = await _cycle(bound, program_id=program.id)
    cohort = await _cohort(bound, cycle_id=cycle.id)
    await _template(bound, program_id=program.id, sequence=1)
    await _member(bound, cohort_id=cohort.id)
    await bound.commit()
    await instantiate_cohort_milestones(cohort_id=cohort.id)

    first = await get_cohort_board(cohort_id=cohort.id)
    calls = {"n": 0}
    real = get_cohort_board_mod.get_cohort_board_db

    async def counting(*args, **kwargs):
        calls["n"] += 1
        return await real(*args, **kwargs)

    monkeypatch.setattr(get_cohort_board_mod, "get_cohort_board_db", counting)
    second = await get_cohort_board(cohort_id=cohort.id)
    assert second == first
    assert calls["n"] == 0


async def test_list_at_risk_empty_is_not_cached(bound):
    program = await _program(bound)
    cycle = await _cycle(bound, program_id=program.id)
    cohort = await _cohort(bound, cycle_id=cycle.id)
    await bound.commit()

    assert await list_at_risk(cohort_id=cohort.id) == []
    key = list_at_risk_mod.cache_key(cohort_id=cohort.id)
    assert await get_redis().get(key) is None
