from datetime import UTC, date, datetime, timedelta

import pytest

from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
from nawa_api.db.cohorts.create_cohort_member_db import create_cohort_member_db
from nawa_api.db.journey.create_assistant_message_db import create_assistant_message_db
from nawa_api.db.journey.create_assistant_thread_db import create_assistant_thread_db
from nawa_api.db.journey.create_digest_db import create_digest_db
from nawa_api.db.journey.create_milestone_db import create_milestone_db
from nawa_api.db.journey.create_milestone_progress_db import create_milestone_progress_db
from nawa_api.db.journey.list_milestone_progress_db import list_milestone_progress_db
from nawa_api.db.journey.list_milestones_db import list_milestones_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.resources.create_resource_chunk_db import create_resource_chunk_db
from nawa_api.db.resources.create_resource_db import create_resource_db
from nawa_api.db.resources.list_resources_db import list_resources_db
from nawa_api.db.resources.list_similar_chunks_db import list_similar_chunks_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.runtime.settings import get_settings

_DIM = get_settings().embeddings_dimension


def _vec(seed: float) -> list[float]:
    v = [0.0] * _DIM
    v[0] = seed
    v[1] = 1.0
    return v


@pytest.mark.asyncio
async def test_milestone_and_progress_lifecycle(db_session):
    program = await create_program_db(
        slug="velocity-journey-test", kind="accelerator", name_en="Velocity", session=db_session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug="c14", name_en="Cycle 14", session=db_session
    )
    manager = await create_user_db(
        email="pm-journey@example.com",
        username="pmjourney",
        password_hash="hashed",
        full_name="PM Journey",
        session=db_session,
    )
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=manager.id,
        starts_at=datetime.now(UTC),
        name_en="Cohort",
        session=db_session,
    )
    template = await create_milestone_db(
        program_id=program.id,
        sequence=1,
        scope="template",
        title_en="Prototype",
        session=db_session,
    )
    milestone = await create_milestone_db(
        program_id=program.id,
        sequence=1,
        scope="cohort",
        cohort_id=cohort.id,
        template_id=template.id,
        title_en="Prototype",
        due_date=date.today() + timedelta(days=30),
        session=db_session,
    )
    assert milestone is not None

    user = await create_user_db(
        email="founder-journey@example.com",
        username="founderjourney",
        password_hash="hashed",
        full_name="Founder Journey",
        session=db_session,
    )
    profile = await create_founder_profile_db(
        user_id=user.id,
        handle="founder-journey",
        display_name_en="Founder Journey",
        session=db_session,
    )
    member = await create_cohort_member_db(
        cohort_id=cohort.id, profile_id=profile.id, session=db_session
    )
    progress = await create_milestone_progress_db(
        milestone_id=milestone.id,
        cohort_member_id=member.id,
        founder_profile_id=profile.id,
        status="in_progress",
        session=db_session,
    )
    assert progress is not None

    rows = await list_milestones_db(cohort_id=cohort.id, session=db_session)
    assert any(m.id == milestone.id for m in rows)
    progress_rows = await list_milestone_progress_db(
        founder_profile_id=profile.id, session=db_session
    )
    assert any(p.id == progress.id for p in progress_rows)


@pytest.mark.asyncio
async def test_resource_and_chunk_similarity_search(db_session):
    resource = await create_resource_db(
        kind="handbook", title_en="Program Handbook", status="live", session=db_session
    )
    chunk_a = await create_resource_chunk_db(
        resource_id=resource.id,
        chunk_index=0,
        content="Fab lab capabilities and equipment.",
        token_count=6,
        source_hash="h1",
        embedding=_vec(1.0),
        session=db_session,
    )
    await create_resource_chunk_db(
        resource_id=resource.id,
        chunk_index=1,
        content="Unrelated chunk about finance.",
        token_count=5,
        source_hash="h2",
        embedding=[0.0, -1.0] + [0.0] * (len(_vec(1.0)) - 2),
        session=db_session,
    )

    live_resources = await list_resources_db(session=db_session)
    assert any(r.id == resource.id for r in live_resources)

    neighbors = await list_similar_chunks_db(query_embedding=_vec(1.0), k=1, session=db_session)
    assert len(neighbors) == 1
    assert neighbors[0][0].id == chunk_a.id


@pytest.mark.asyncio
async def test_draft_resource_excluded_from_list_and_similarity(db_session):
    resource = await create_resource_db(
        kind="faq", title_en="Draft FAQ", status="draft", session=db_session
    )
    await create_resource_chunk_db(
        resource_id=resource.id,
        chunk_index=0,
        content="Draft content",
        token_count=2,
        source_hash="hdraft",
        embedding=_vec(1.0),
        session=db_session,
    )
    live_resources = await list_resources_db(session=db_session)
    assert not any(r.id == resource.id for r in live_resources)

    neighbors = await list_similar_chunks_db(query_embedding=_vec(1.0), k=5, session=db_session)
    assert not any(c.resource_id == resource.id for c, _ in neighbors)


@pytest.mark.asyncio
async def test_assistant_thread_and_message_and_digest(db_session):
    user = await create_user_db(
        email="assistant-user@example.com",
        username="assistantuser",
        password_hash="hashed",
        full_name="Assistant User",
        session=db_session,
    )
    thread = await create_assistant_thread_db(
        user_id=user.id, kind="assistant", language="ar", session=db_session
    )
    assert thread is not None
    message = await create_assistant_message_db(
        thread_id=thread.id,
        role="assistant",
        content="إجابة تجريبية",
        citations=[{"resource_chunk_id": "abc", "title": "handbook"}],
        session=db_session,
    )
    assert message is not None

    digest = await create_digest_db(
        kind="cohort",
        scope_type="cohort",
        scope_id=user.id,  # placeholder scope id (uuid shape only, not a real cohort)
        period_start=date.today(),
        period_end=date.today() + timedelta(days=7),
        content_en="Weekly digest narrative.",
        session=db_session,
    )
    assert digest is not None
