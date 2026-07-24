import uuid

import pytest_asyncio
from sqlalchemy import select, update

from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.update_application_normalization_db import (
    update_application_normalization_db,
)
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.jobs.embed_application import embed_application
from nawa_api.models.ai import ApplicationEmbedding


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _normalized_application(session, *, title: str, summary: str):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", name_en="P", kind="competition", session=session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=session
    )
    app = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="Amina",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "great idea"},
        session=session,
    )
    await update_application_normalization_db(
        application_id=app.id,
        source_language="en",
        normalized={"title": title, "summary": summary},
        title=title,
        summary=summary,
        session=session,
    )
    return app


async def test_embed_creates_a_row_with_a_vector(bound):
    app = await _normalized_application(
        bound, title="Water sensors", summary="Low-cost sensors for farms."
    )
    await bound.commit()

    result = await embed_application(application_id=str(app.id))
    assert result == "embedded"

    row = (
        await bound.execute(
            select(ApplicationEmbedding).where(ApplicationEmbedding.application_id == app.id)
        )
    ).scalar_one()
    assert row.embedding is not None
    assert row.embedding_model == "mock"
    assert row.source_hash


async def test_second_run_is_idempotent_noop(bound):
    app = await _normalized_application(bound, title="T", summary="S")
    await bound.commit()

    r1 = await embed_application(application_id=str(app.id))
    r2 = await embed_application(application_id=str(app.id))
    assert r1 == "embedded"
    assert r2 == "unchanged"


async def test_seed_vectors_are_replaced(bound):
    app = await _normalized_application(bound, title="T", summary="S")
    await bound.commit()
    await embed_application(application_id=str(app.id))

    await bound.execute(
        update(ApplicationEmbedding)
        .where(ApplicationEmbedding.application_id == app.id)
        .values(embedding_model="seed-deterministic-v1")
    )
    await bound.commit()

    result = await embed_application(application_id=str(app.id))
    assert result == "embedded"  # re-embedded: stored model was the seed's, not the real provider

    row = (
        await bound.execute(
            select(ApplicationEmbedding).where(ApplicationEmbedding.application_id == app.id)
        )
    ).scalar_one()
    assert row.embedding_model == "mock"


async def test_title_summary_change_reembeds(bound):
    app = await _normalized_application(bound, title="Original", summary="Original summary.")
    await bound.commit()
    r1 = await embed_application(application_id=str(app.id))
    assert r1 == "embedded"

    await update_application_normalization_db(
        application_id=app.id,
        source_language="en",
        normalized={"title": "Changed", "summary": "Changed summary."},
        title="Changed",
        summary="Changed summary.",
        session=bound,
    )
    await bound.commit()

    r2 = await embed_application(application_id=str(app.id))
    assert r2 == "embedded"  # content hash changed -> re-embedded, not "unchanged"


async def test_missing_application_returns_missing(bound):
    assert await embed_application(application_id=str(uuid.uuid4())) == "missing"
