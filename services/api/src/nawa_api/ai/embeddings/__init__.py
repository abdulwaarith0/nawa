"""Embeddings registry + gateway (05-ai-infrastructure.md §4).

`embed(texts, *, pii=...)` is the single entry point. The `pii` flag has NO
default — every call site must decide: True pseudonymizes applicant/member text
before it leaves; False asserts the content is institutional (handbooks, lab
sheets). Batching respects EMBED_BATCH_SIZE and a global Redis quota; arq workers
respect the quota by sleeping, never by dropping work.
"""

from __future__ import annotations

import asyncio

from nawa_api.ai.embeddings.base import (
    EMBED_BATCH_SIZE,
    EMBED_RATE_PER_MIN,
    EMBEDDINGS_DIMENSION,
    EmbeddingsProvider,
)
from nawa_api.ai.embeddings.mock_embeddings import MockEmbeddingsProvider
from nawa_api.ai.pii import KnownEntities, pseudonymize
from nawa_api.contracts.errors import ERR_AI_NOT_CONFIGURED
from nawa_api.runtime.redis import get_redis
from nawa_api.runtime.settings import get_settings

_QUOTA_KEY = "rl:embeddings:global"
_singletons: dict[str, EmbeddingsProvider] = {}


def _build(name: str) -> EmbeddingsProvider:
    if name == "mock":
        return MockEmbeddingsProvider()
    if name == "openai":
        try:
            from nawa_api.ai.embeddings.openai_embeddings import OpenAIEmbeddingsProvider
        except ImportError as exc:  # pragma: no cover - SDK not installed offline
            raise ERR_AI_NOT_CONFIGURED from exc
        return OpenAIEmbeddingsProvider()
    raise ERR_AI_NOT_CONFIGURED


def get_embeddings_provider(name: str | None = None) -> EmbeddingsProvider:
    settings = get_settings()
    resolved = "mock" if settings.environment == "test" else (name or settings.embeddings_provider)
    if resolved not in _singletons:
        _singletons[resolved] = _build(resolved)
    return _singletons[resolved]


def reset_embeddings_cache() -> None:
    _singletons.clear()


def _pseudonymize_for_embedding(text: str) -> str:
    # One-way: vectors are never rehydrated, so the mapping is discarded.
    return pseudonymize(text, KnownEntities())[0]


async def _reserve_quota(count: int) -> None:
    redis = get_redis()
    try:
        total = await redis.incrby(_QUOTA_KEY, count)
        if total == count:
            await redis.expire(_QUOTA_KEY, 60)
    except Exception:  # pragma: no cover - degrade open on Redis error
        return
    if total > EMBED_RATE_PER_MIN and get_settings().environment != "test":  # pragma: no cover
        ttl = await redis.ttl(_QUOTA_KEY)
        if ttl > 0:
            await asyncio.sleep(ttl)


async def embed(texts: list[str], *, pii: bool) -> list[list[float]]:
    if not texts:
        return []
    provider = get_embeddings_provider()
    prepared = [_pseudonymize_for_embedding(t) for t in texts] if pii else list(texts)
    out: list[list[float]] = []
    for i in range(0, len(prepared), EMBED_BATCH_SIZE):
        batch = prepared[i : i + EMBED_BATCH_SIZE]
        await _reserve_quota(len(batch))
        out.extend(await provider.embed_batch(batch))
    return out


__all__ = [
    "EMBEDDINGS_DIMENSION",
    "EMBED_BATCH_SIZE",
    "embed",
    "get_embeddings_provider",
    "reset_embeddings_cache",
]
