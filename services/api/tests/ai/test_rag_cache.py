import uuid

from nawa_api.ai.rag.retrieve import RetrievalFilters, RetrievedChunk
from nawa_api.runtime.redis import get_redis
from nawa_api.services.rag import retrieve_chunks as mod
from nawa_api.services.rag.retrieve_chunks import (
    cache_key,
    invalidate_retrieval_cache,
    retrieve_chunks,
)


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(), resource_id=uuid.uuid4(), content="handbook text", score=0.9
    )


async def test_result_is_cached_and_reused(monkeypatch):
    calls: list[str] = []

    async def fake_retrieve(query, *, k=8, filters=None):
        calls.append(query)
        return [_chunk()]

    monkeypatch.setattr(mod, "retrieve", fake_retrieve)
    query = f"q-{uuid.uuid4()}"
    await get_redis().delete(cache_key(query, 8, RetrievalFilters()))

    first = await retrieve_chunks(query)
    second = await retrieve_chunks(query)
    assert len(calls) == 1  # second call served from cache
    assert [c.chunk_id for c in first] == [c.chunk_id for c in second]


async def test_empty_result_is_not_cached(monkeypatch):
    calls: list[str] = []

    async def fake_retrieve(query, *, k=8, filters=None):
        calls.append(query)
        return []

    monkeypatch.setattr(mod, "retrieve", fake_retrieve)
    query = f"empty-{uuid.uuid4()}"
    await retrieve_chunks(query)
    await retrieve_chunks(query)
    assert len(calls) == 2  # empty never cached → recomputed each time


async def test_invalidation_clears_the_cache(monkeypatch):
    calls: list[str] = []

    async def fake_retrieve(query, *, k=8, filters=None):
        calls.append(query)
        return [_chunk()]

    monkeypatch.setattr(mod, "retrieve", fake_retrieve)
    query = f"inv-{uuid.uuid4()}"
    await get_redis().delete(cache_key(query, 8, RetrievalFilters()))

    await retrieve_chunks(query)  # caches
    await invalidate_retrieval_cache()
    await retrieve_chunks(query)  # recomputed after invalidation
    assert len(calls) == 2
