"""Cached RAG retrieval (05-ai-infrastructure.md §9.4 / §11).

Retrieval results ARE cacheable (TTL 600s), invalidated by any resource write
via the `services:rag:retrieve:*` glob. Generated answers are NEVER cached
(conversational turns per canon). An empty result is never cached (canon).
"""

from __future__ import annotations

import json
from hashlib import sha256

from pydantic import BaseModel

from nawa_api.ai.rag.retrieve import RetrievalFilters, RetrievedChunk, retrieve
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys

CACHE_TTL_SECONDS = 600
_KEY_PREFIX = "services:rag:retrieve"


class _CachedChunks(BaseModel):
    items: list[RetrievedChunk]


def cache_key(query: str, k: int, filters: RetrievalFilters) -> str:
    raw = json.dumps(
        {"q": query, "k": k, "f": filters.model_dump()}, sort_keys=True, ensure_ascii=False
    )
    return f"{_KEY_PREFIX}:{sha256(raw.encode('utf-8')).hexdigest()[:24]}"


async def retrieve_chunks(
    query: str, *, k: int = 8, filters: RetrievalFilters | None = None
) -> list[RetrievedChunk]:
    filters = filters or RetrievalFilters()
    key = cache_key(query, k, filters)
    cached = await redis_retrieve_key(key, _CachedChunks)
    if cached is not None:
        return cached.items
    items = await retrieve(query, k=k, filters=filters)
    if items:  # never cache an empty result (canon)
        await redis_update_key(key, _CachedChunks(items=items), CACHE_TTL_SECONDS)
    return items


async def invalidate_retrieval_cache() -> None:
    """Called by resource write services after any corpus change."""
    await invalidate_cache_keys(f"{_KEY_PREFIX}:*")
