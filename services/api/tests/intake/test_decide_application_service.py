import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import select

from nawa_api.contracts.errors import ApiError
from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.create_scorecard_db import create_scorecard_db
from nawa_api.db.intake.update_application_scoring_db import update_application_scoring_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.models.identity import User
from nawa_api.models.intake import Decision
from nawa_api.models.programs import CohortMember
from nawa_api.runtime.redis import get_redis
from nawa_api.services.intake import decide_application as decide_application_mod
from nawa_api.services.intake.decide_application import decide_application
from nawa_api.services.intake.get_scorecard import cache_key as scorecard_cache_key
from nawa_api.services.intake.list_shortlist import cache_key as shortlist_cache_key

_CRITERIA = [{"key": "novelty", "weight": 1.0, "scale_max": 10}]
_SMALL_CAPACITY_CONFIG = {"intake": {"shortlist_capacity": 1, "waitlist_capacity": 1}}


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _cycle_with_rubric(session, *, cycle_config=None):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id,
        slug=f"c-{uuid.uuid4().hex[:8]}",
        name_en="C",
        config=cycle_config,
        session=session,
    )
    rubric = await create_rubric_db(
        program_id=program.id,
        version=1,
        criteria=_CRITERIA,
        name_en="R",
        status="active",
        session=session,
    )
    return program, cycle, rubric


async def _scored_application(session, *, cycle_id, rubric_id, total_score, email=None):
    app = await create_application_db(
        cycle_id=cycle_id,
        applicant_name="Amina Al-Sayed",
        applicant_email=email or f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "great idea"},
        session=session,
    )
    await update_application_scoring_db(
        application_id=app.id, total_score=total_score, session=session
    )
    await create_scorecard_db(
        application_id=app.id,
        rubric_id=rubric_id,
        rubric_version=1,
        prompt_version="v2",
        source="ai",
        total_score=total_score,
        session=session,
    )
    return app


async def _reviewer(session):
    return await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"r{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="Reviewer",
        session=session,
    )


async def test_missing_application_raises_not_found(bound):
    reviewer = await _reviewer(bound)
    await bound.commit()
    with pytest.raises(ApiError):
        await decide_application(
            application_id=uuid.uuid4(),
            decision="shortlist",
            reason=None,
            cohort_id=None,
            decided_by=reviewer.id,
        )


async def test_invalid_decision_value_raises(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    app = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10)
    reviewer = await _reviewer(bound)
    await bound.commit()
    with pytest.raises(ApiError):
        await decide_application(
            application_id=app.id,
            decision="maybe",
            reason=None,
            cohort_id=None,
            decided_by=reviewer.id,
        )


async def test_application_not_yet_scored_raises(bound):
    _program, cycle, _rubric = await _cycle_with_rubric(bound)
    app = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="A",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "x"},
        session=bound,
    )
    reviewer = await _reviewer(bound)
    await bound.commit()
    with pytest.raises(ApiError):
        await decide_application(
            application_id=app.id,
            decision="shortlist",
            reason=None,
            cohort_id=None,
            decided_by=reviewer.id,
        )


async def test_matching_ai_band_needs_no_reason(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    # capacity 1/1: the single highest scorer is rank 1 -> AI band "shortlist"
    top = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    reviewer = await _reviewer(bound)
    await bound.commit()

    result = await decide_application(
        application_id=top.id,
        decision="shortlist",
        reason=None,
        cohort_id=None,
        decided_by=reviewer.id,
    )
    assert result["ai_band"] == "shortlist"
    assert result["overridden"] is False
    assert result["status"] == "shortlisted"


async def test_diverging_from_ai_band_requires_reason(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    top = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    reviewer = await _reviewer(bound)
    await bound.commit()

    with pytest.raises(ApiError):
        await decide_application(
            application_id=top.id,
            decision="reject",  # diverges from the "shortlist" AI band, rank 1
            reason=None,
            cohort_id=None,
            decided_by=reviewer.id,
        )


async def test_diverging_with_reason_succeeds_and_marks_overridden(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    top = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    reviewer = await _reviewer(bound)
    await bound.commit()

    result = await decide_application(
        application_id=top.id,
        decision="reject",
        reason="Idea already covered by an existing venture.",
        cohort_id=None,
        decided_by=reviewer.id,
    )
    assert result["overridden"] is True
    assert result["status"] == "decided"


async def test_previous_value_snapshot_shape(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    top = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    reviewer = await _reviewer(bound)
    await bound.commit()

    await decide_application(
        application_id=top.id,
        decision="shortlist",
        reason=None,
        cohort_id=None,
        decided_by=reviewer.id,
    )
    row = (
        await bound.execute(select(Decision).where(Decision.application_id == top.id))
    ).scalar_one()
    assert row.previous_value == {
        "status": "scored",
        "ai_total_score": 90.0,
        "ai_band": "shortlist",
        "rubric_version": 1,
    }
    assert row.new_value == {"status": "shortlisted"}


async def test_accept_without_cohort_id_raises(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    top = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    reviewer = await _reviewer(bound)
    await bound.commit()

    with pytest.raises(ApiError):
        await decide_application(
            application_id=top.id,
            decision="accept",
            reason=None,
            cohort_id=None,
            decided_by=reviewer.id,
        )


async def test_non_accept_with_cohort_id_raises(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    top = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    reviewer = await _reviewer(bound)
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=reviewer.id,
        starts_at=datetime.now(UTC),
        name_en="Cohort",
        session=bound,
    )
    await bound.commit()

    with pytest.raises(ApiError):
        await decide_application(
            application_id=top.id,
            decision="shortlist",
            reason=None,
            cohort_id=cohort.id,
            decided_by=reviewer.id,
        )


async def test_accept_with_cohort_from_different_cycle_raises(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    _program2, other_cycle, _rubric2 = await _cycle_with_rubric(bound)
    top = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    reviewer = await _reviewer(bound)
    foreign_cohort = await create_cohort_db(
        cycle_id=other_cycle.id,
        program_manager_user_id=reviewer.id,
        starts_at=datetime.now(UTC),
        name_en="Foreign Cohort",
        session=bound,
    )
    await bound.commit()

    with pytest.raises(ApiError):
        await decide_application(
            application_id=top.id,
            decision="accept",
            reason=None,
            cohort_id=foreign_cohort.id,
            decided_by=reviewer.id,
        )


async def test_accept_creates_user_profile_and_cohort_membership(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    email = f"{uuid.uuid4().hex[:8]}@newfounder.io"
    top = await _scored_application(
        bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90, email=email
    )
    reviewer = await _reviewer(bound)
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=reviewer.id,
        starts_at=datetime.now(UTC),
        name_en="Cohort",
        session=bound,
    )
    await bound.commit()

    result = await decide_application(
        application_id=top.id,
        decision="accept",
        reason=None,
        cohort_id=cohort.id,
        decided_by=reviewer.id,
    )
    assert result["status"] == "decided"
    assert result["profile_id"] is not None

    new_user = (
        await bound.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    assert new_user is not None

    members = (
        await bound.execute(
            select(CohortMember).where(CohortMember.cohort_id == cohort.id)
        )
    ).scalars().all()
    assert len(members) == 1
    assert str(members[0].profile_id) == result["profile_id"]


async def test_accept_is_idempotent_no_duplicate_membership(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    email = f"{uuid.uuid4().hex[:8]}@newfounder.io"
    top = await _scored_application(
        bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90, email=email
    )
    reviewer = await _reviewer(bound)
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=reviewer.id,
        starts_at=datetime.now(UTC),
        name_en="Cohort",
        session=bound,
    )
    await bound.commit()

    first = await decide_application(
        application_id=top.id,
        decision="accept",
        reason=None,
        cohort_id=cohort.id,
        decided_by=reviewer.id,
    )
    second = await decide_application(
        application_id=top.id,
        decision="accept",
        reason=None,
        cohort_id=cohort.id,
        decided_by=reviewer.id,
    )
    assert first["profile_id"] == second["profile_id"]  # same profile reused, not recreated

    members = (
        await bound.execute(
            select(CohortMember).where(CohortMember.cohort_id == cohort.id)
        )
    ).scalars().all()
    assert len(members) == 1  # re-accepting is a no-op, not a duplicate row

    decisions = (
        await bound.execute(select(Decision).where(Decision.application_id == top.id))
    ).scalars().all()
    assert len(decisions) == 2  # but the decision itself IS append-only, per spec


async def test_cache_invalidation_fires(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    top = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    reviewer = await _reviewer(bound)
    await bound.commit()

    redis = get_redis()
    shortlist_key = shortlist_cache_key(
        cycle_id=cycle.id,
        score_band=None,
        criterion=None,
        criterion_min=None,
        flags=frozenset(),
        language=None,
        country=None,
        decision=None,
        q=None,
        limit=100,
        offset=0,
    )
    await redis.set(shortlist_key, '{"items": [1]}')
    scorecard_key = scorecard_cache_key(top.id)
    await redis.set(scorecard_key, '{"item": {}}')

    await decide_application(
        application_id=top.id,
        decision="shortlist",
        reason=None,
        cohort_id=None,
        decided_by=reviewer.id,
    )
    assert await redis.get(shortlist_key) is None
    assert await redis.get(scorecard_key) is None


async def test_no_active_rubric_still_computes_a_band(bound):
    # Rubric left in "draft" -> get_active_rubric_db finds nothing, so
    # rubric_version stays None, but ranking/banding must still work off
    # ai_total_score alone.
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=bound
    )
    cycle = await create_program_cycle_db(
        program_id=program.id,
        slug=f"c-{uuid.uuid4().hex[:8]}",
        name_en="C",
        config=_SMALL_CAPACITY_CONFIG,
        session=bound,
    )
    draft_rubric = await create_rubric_db(
        program_id=program.id,
        version=1,
        criteria=_CRITERIA,
        name_en="R",
        status="draft",
        session=bound,
    )
    top = await _scored_application(
        bound, cycle_id=cycle.id, rubric_id=draft_rubric.id, total_score=90
    )
    reviewer = await _reviewer(bound)
    await bound.commit()

    result = await decide_application(
        application_id=top.id,
        decision="shortlist",
        reason=None,
        cohort_id=None,
        decided_by=reviewer.id,
    )
    assert result["ai_band"] == "shortlist"

    row = (
        await bound.execute(select(Decision).where(Decision.application_id == top.id))
    ).scalar_one()
    assert row.previous_value["rubric_version"] is None


async def test_accept_reuses_an_existing_user_with_no_profile_yet(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    email = f"{uuid.uuid4().hex[:8]}@already-a-user.io"
    existing_user = await create_user_db(
        email=email,
        username=f"u{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="Existing User",
        session=bound,
    )
    top = await _scored_application(
        bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90, email=email
    )
    reviewer = await _reviewer(bound)
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=reviewer.id,
        starts_at=datetime.now(UTC),
        name_en="Cohort",
        session=bound,
    )
    await bound.commit()

    result = await decide_application(
        application_id=top.id,
        decision="accept",
        reason=None,
        cohort_id=cohort.id,
        decided_by=reviewer.id,
    )
    assert result["profile_id"] is not None

    users = (
        await bound.execute(select(User).where(User.email == email))
    ).scalars().all()
    assert len(users) == 1
    assert users[0].id == existing_user.id  # no duplicate user created


async def test_accept_reuses_an_existing_profile_from_another_application(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    email = f"{uuid.uuid4().hex[:8]}@already-a-founder.io"
    existing_user = await create_user_db(
        email=email,
        username=f"u{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="Existing Founder",
        session=bound,
    )
    existing_profile = await create_founder_profile_db(
        user_id=existing_user.id,
        handle=f"h-{uuid.uuid4().hex[:8]}",
        display_name_en="Existing Founder",
        session=bound,
    )
    top = await _scored_application(
        bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90, email=email
    )
    reviewer = await _reviewer(bound)
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=reviewer.id,
        starts_at=datetime.now(UTC),
        name_en="Cohort",
        session=bound,
    )
    await bound.commit()

    result = await decide_application(
        application_id=top.id,
        decision="accept",
        reason=None,
        cohort_id=cohort.id,
        decided_by=reviewer.id,
    )
    assert result["profile_id"] == str(existing_profile.id)  # reused, not recreated


async def test_raises_internal_when_user_creation_fails(bound, monkeypatch):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    top = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    reviewer = await _reviewer(bound)
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=reviewer.id,
        starts_at=datetime.now(UTC),
        name_en="Cohort",
        session=bound,
    )
    await bound.commit()

    async def fail(**kwargs):
        return None

    monkeypatch.setattr(decide_application_mod, "create_user_db", fail)
    with pytest.raises(ApiError):
        await decide_application(
            application_id=top.id,
            decision="accept",
            reason=None,
            cohort_id=cohort.id,
            decided_by=reviewer.id,
        )


async def test_raises_internal_when_profile_creation_fails(bound, monkeypatch):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    top = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    reviewer = await _reviewer(bound)
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=reviewer.id,
        starts_at=datetime.now(UTC),
        name_en="Cohort",
        session=bound,
    )
    await bound.commit()

    async def fail(**kwargs):
        return None

    monkeypatch.setattr(decide_application_mod, "create_founder_profile_db", fail)
    with pytest.raises(ApiError):
        await decide_application(
            application_id=top.id,
            decision="accept",
            reason=None,
            cohort_id=cohort.id,
            decided_by=reviewer.id,
        )


async def test_raises_internal_when_profile_link_update_fails(bound, monkeypatch):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    top = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    reviewer = await _reviewer(bound)
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=reviewer.id,
        starts_at=datetime.now(UTC),
        name_en="Cohort",
        session=bound,
    )
    await bound.commit()

    async def fail(**kwargs):
        return False

    monkeypatch.setattr(decide_application_mod, "update_application_profile_link_db", fail)
    with pytest.raises(ApiError):
        await decide_application(
            application_id=top.id,
            decision="accept",
            reason=None,
            cohort_id=cohort.id,
            decided_by=reviewer.id,
        )


async def test_raises_internal_when_decision_write_fails(bound, monkeypatch):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    top = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    reviewer = await _reviewer(bound)
    await bound.commit()

    async def fail(**kwargs):
        return None

    monkeypatch.setattr(decide_application_mod, "create_decision_db", fail)
    with pytest.raises(ApiError):
        await decide_application(
            application_id=top.id,
            decision="shortlist",
            reason=None,
            cohort_id=None,
            decided_by=reviewer.id,
        )


async def test_raises_internal_when_status_update_fails(bound, monkeypatch):
    _program, cycle, rubric = await _cycle_with_rubric(bound, cycle_config=_SMALL_CAPACITY_CONFIG)
    top = await _scored_application(bound, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90)
    reviewer = await _reviewer(bound)
    await bound.commit()

    async def fail(**kwargs):
        return False

    monkeypatch.setattr(decide_application_mod, "update_application_decision_status_db", fail)
    with pytest.raises(ApiError):
        await decide_application(
            application_id=top.id,
            decision="shortlist",
            reason=None,
            cohort_id=None,
            decided_by=reviewer.id,
        )
