import uuid

import pytest_asyncio
from sqlalchemy import select

from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_application_embedding_db import create_application_embedding_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.jobs.dedup_scan import dedup_scan
from nawa_api.models.intake import DedupMatch
from nawa_api.seed_data.embeddings import deterministic_vector, near_duplicate_vector
from nawa_api.services.site_config.update_site_config import update_site_config


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    await update_site_config(key="intake:dedup_threshold", value=0.83)
    return db_session


async def _cycle(session):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", name_en="P", kind="competition", session=session
    )
    return await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=session
    )


async def _application(session, *, cycle_id, email=None):
    return await create_application_db(
        cycle_id=cycle_id,
        applicant_name="Amina",
        applicant_email=email or f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "great idea"},
        session=session,
    )


async def _matches_for(session, application_id):
    # No expire_all() here: DedupMatch rows are always written through the
    # job's own separate session, never through `bound`, so `bound` never
    # holds a stale DedupMatch instance that would need refreshing — and
    # expiring the whole session would also expire unrelated Application
    # objects the test still holds live references to.
    stmt = select(DedupMatch).where(DedupMatch.application_id == application_id)
    rows = (await session.execute(stmt)).scalars()
    return list(rows)


async def test_similar_embedding_above_threshold_creates_a_match(bound):
    cycle = await _cycle(bound)
    app_a = await _application(bound, cycle_id=cycle.id)
    app_b = await _application(bound, cycle_id=cycle.id)
    base = deterministic_vector(f"cluster-{uuid.uuid4()}")
    await create_application_embedding_db(
        application_id=app_a.id,
        embedding=base,
        embedding_model="mock",
        source_hash="h1",
        session=bound,
    )
    await create_application_embedding_db(
        application_id=app_b.id,
        embedding=near_duplicate_vector(base, noise_key=f"dup-{app_b.id}"),
        embedding_model="mock",
        source_hash="h2",
        session=bound,
    )
    await bound.commit()
    app_b_id = app_b.id

    count = await dedup_scan(application_id=str(app_a.id))
    assert count == 1

    matches = await _matches_for(bound, app_a.id)
    assert len(matches) == 1
    assert matches[0].matched_application_id == app_b_id
    assert matches[0].status == "pending"
    assert matches[0].similarity >= 0.83


async def test_dissimilar_embedding_below_threshold_creates_no_match(bound):
    cycle = await _cycle(bound)
    app_a = await _application(bound, cycle_id=cycle.id)
    app_b = await _application(bound, cycle_id=cycle.id)
    # Two independently-random unit vectors in high dimension are ~orthogonal
    # (cosine ~0), well under the 0.83 floor.
    await create_application_embedding_db(
        application_id=app_a.id,
        embedding=deterministic_vector(f"a-{uuid.uuid4()}"),
        embedding_model="mock",
        source_hash="h1",
        session=bound,
    )
    await create_application_embedding_db(
        application_id=app_b.id,
        embedding=deterministic_vector(f"b-{uuid.uuid4()}"),
        embedding_model="mock",
        source_hash="h2",
        session=bound,
    )
    await bound.commit()

    count = await dedup_scan(application_id=str(app_a.id))
    assert count == 0
    assert await _matches_for(bound, app_a.id) == []


async def test_exact_email_match_across_different_cycles(bound):
    cycle_a = await _cycle(bound)
    cycle_b = await _cycle(bound)
    shared_email = f"{uuid.uuid4().hex[:8]}@resubmitter.io"
    app_a = await _application(bound, cycle_id=cycle_a.id, email=shared_email)
    app_b = await _application(bound, cycle_id=cycle_b.id, email=shared_email)
    await bound.commit()
    app_b_id = app_b.id

    # No embeddings at all — the email match alone must surface the pair.
    count = await dedup_scan(application_id=str(app_a.id))
    assert count == 1

    matches = await _matches_for(bound, app_a.id)
    assert matches[0].matched_application_id == app_b_id
    assert matches[0].similarity == 1.0


async def test_rerunning_the_scan_converges_no_duplicate_rows(bound):
    cycle = await _cycle(bound)
    shared_email = f"{uuid.uuid4().hex[:8]}@resubmitter.io"
    app_a = await _application(bound, cycle_id=cycle.id, email=shared_email)
    await _application(bound, cycle_id=cycle.id, email=shared_email)
    await bound.commit()

    await dedup_scan(application_id=str(app_a.id))
    await dedup_scan(application_id=str(app_a.id))

    matches = await _matches_for(bound, app_a.id)
    assert len(matches) == 1  # upsert converges, does not duplicate


async def test_missing_application_returns_zero(bound):
    assert await dedup_scan(application_id=str(uuid.uuid4())) == 0
