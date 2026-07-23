import uuid

import pytest_asyncio
from sqlalchemy import select, update

from nawa_api.db.resources.create_resource_db import create_resource_db
from nawa_api.jobs.embed_resource import embed_resource
from nawa_api.models.journey import Resource, ResourceChunk


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _resource(session, content: str):
    return await create_resource_db(
        kind="handbook",
        title_en="T",
        language="en",
        content=content,
        status="live",
        session=session,
    )


async def _chunks(session, resource_id):
    rows = await session.execute(
        select(ResourceChunk).where(ResourceChunk.resource_id == resource_id)
    )
    return rows.scalars().all()


async def test_embed_creates_chunks_with_vectors(bound):
    res = await _resource(bound, "# Guide\nround two details here. teams build fast in the lab.")
    await bound.commit()

    n = await embed_resource(resource_id=str(res.id))
    assert n >= 1
    rows = await _chunks(bound, res.id)
    assert len(rows) == n
    assert all(r.embedding is not None for r in rows)
    assert all(r.embedding_model == "mock" for r in rows)
    assert all(r.source_hash for r in rows)


async def test_second_run_is_idempotent_noop(bound):
    res = await _resource(bound, "content here. and more content.")
    await bound.commit()
    n1 = await embed_resource(resource_id=str(res.id))
    n2 = await embed_resource(resource_id=str(res.id))
    assert n1 >= 1
    assert n2 == 0  # unchanged → skip


async def test_seed_vectors_are_replaced(bound):
    res = await _resource(bound, "alpha sentence. beta sentence.")
    await bound.commit()
    n1 = await embed_resource(resource_id=str(res.id))
    # Simulate seeded pseudo-vectors on the existing rows.
    await bound.execute(
        update(ResourceChunk)
        .where(ResourceChunk.resource_id == res.id)
        .values(embedding_model="seed")
    )
    await bound.commit()
    n2 = await embed_resource(resource_id=str(res.id))
    assert n2 == n1  # re-embedded because the stored model was 'seed', not 'mock'


async def test_content_change_reembeds(bound):
    res = await _resource(bound, "original words here. one two.")
    await bound.commit()
    await embed_resource(resource_id=str(res.id))
    await bound.execute(
        update(Resource)
        .where(Resource.id == res.id)
        .values(content="# H\ncompletely different text now. three four five.")
    )
    await bound.commit()
    n2 = await embed_resource(resource_id=str(res.id))
    assert n2 >= 1  # content hash changed → re-embedded


async def test_no_content_returns_zero_and_clears_chunks(bound):
    res = await _resource(bound, "some text to embed.")
    await bound.commit()
    await embed_resource(resource_id=str(res.id))
    await bound.execute(update(Resource).where(Resource.id == res.id).values(content=None))
    await bound.commit()
    n = await embed_resource(resource_id=str(res.id))
    assert n == 0
    assert await _chunks(bound, res.id) == []


async def test_missing_resource_returns_zero(bound):
    assert await embed_resource(resource_id=str(uuid.uuid4())) == 0
