import uuid

import pytest_asyncio

from nawa_api.ai.embeddings.mock_embeddings import deterministic_vector
from nawa_api.ai.rag.retrieve import RetrievalFilters, retrieve
from nawa_api.db.resources.create_resource_chunk_db import create_resource_chunk_db
from nawa_api.db.resources.create_resource_db import create_resource_db
from nawa_api.models.journey import ResourceChunk


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    # retrieve()/search_chunks_db open their own session — bind the global
    # factory to the throwaway test DB so they see this test's committed rows.
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _resource(session, *, kind="handbook", language="en", status="live"):
    return await create_resource_db(
        kind=kind, title_en="T", language=language, content="c", status=status, session=session
    )


async def _chunk(session, resource_id, *, content, embedding, language="en"):
    return await create_resource_chunk_db(
        resource_id=resource_id,
        chunk_index=0,
        content=content,
        token_count=5,
        source_hash="h",
        language=language,
        embedding=embedding,
        embedding_model="mock",
        session=session,
    )


async def test_exact_match_ranks_first_and_min_score_drops_noise(bound):
    query = f"handbook round {uuid.uuid4()}"
    vec = deterministic_vector(query)
    r1 = await _resource(bound)
    match = await _chunk(bound, r1.id, content="round 2 details", embedding=vec)
    r2 = await _resource(bound)
    await _chunk(
        bound, r2.id, content="noise", embedding=deterministic_vector(f"noise {uuid.uuid4()}")
    )
    await bound.commit()

    out = await retrieve(query, k=8)
    assert [c.chunk_id for c in out] == [match.id]  # noise dropped below RAG_MIN_SCORE
    assert out[0].score >= 0.25


async def test_language_filter(bound):
    query = f"guide {uuid.uuid4()}"
    vec = deterministic_vector(query)
    ren = await _resource(bound, language="en")
    await _chunk(bound, ren.id, content="en text", embedding=vec, language="en")
    rar = await _resource(bound, language="ar")
    await _chunk(bound, rar.id, content="ar text", embedding=vec, language="ar")
    await bound.commit()

    out = await retrieve(query, filters=RetrievalFilters(language="en"))
    assert [c.content for c in out] == ["en text"]


async def test_resource_type_filter(bound):
    query = f"policy {uuid.uuid4()}"
    vec = deterministic_vector(query)
    rh = await _resource(bound, kind="handbook")
    await _chunk(bound, rh.id, content="handbook text", embedding=vec)
    rf = await _resource(bound, kind="faq")
    await _chunk(bound, rf.id, content="faq text", embedding=vec)
    await bound.commit()

    out = await retrieve(query, filters=RetrievalFilters(resource_type="faq"))
    assert [c.content for c in out] == ["faq text"]


async def test_program_id_metadata_filter(bound):
    query = f"program {uuid.uuid4()}"
    vec = deterministic_vector(query)
    rsos = await _resource(bound)
    rxlr = await _resource(bound)
    bound.add(
        ResourceChunk(
            resource_id=rsos.id,
            chunk_index=0,
            content="sos chunk",
            token_count=5,
            source_hash="h",
            language="en",
            embedding=vec,
            embedding_model="mock",
            chunk_metadata={"program_id": "sos"},
        )
    )
    bound.add(
        ResourceChunk(
            resource_id=rxlr.id,
            chunk_index=0,
            content="xlr chunk",
            token_count=5,
            source_hash="h",
            language="en",
            embedding=vec,
            embedding_model="mock",
            chunk_metadata={"program_id": "velocity"},
        )
    )
    await bound.commit()

    out = await retrieve(query, filters=RetrievalFilters(program_id="sos"))
    assert [c.content for c in out] == ["sos chunk"]


async def test_audience_metadata_filter(bound):
    query = f"audience {uuid.uuid4()}"
    vec = deterministic_vector(query)
    r1 = await _resource(bound)
    r2 = await _resource(bound)
    bound.add(
        ResourceChunk(
            resource_id=r1.id,
            chunk_index=0,
            content="founder chunk",
            token_count=5,
            source_hash="h",
            language="en",
            embedding=vec,
            embedding_model="mock",
            chunk_metadata={"audience": "founder"},
        )
    )
    bound.add(
        ResourceChunk(
            resource_id=r2.id,
            chunk_index=0,
            content="staff chunk",
            token_count=5,
            source_hash="h",
            language="en",
            embedding=vec,
            embedding_model="mock",
            chunk_metadata={"audience": "staff"},
        )
    )
    await bound.commit()

    out = await retrieve(query, filters=RetrievalFilters(audience="founder"))
    assert [c.content for c in out] == ["founder chunk"]


async def test_draft_resources_are_excluded(bound):
    query = f"draft {uuid.uuid4()}"
    vec = deterministic_vector(query)
    draft = await _resource(bound, status="draft")
    await _chunk(bound, draft.id, content="draft text", embedding=vec)
    await bound.commit()

    assert await retrieve(query) == []
