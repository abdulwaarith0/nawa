import math

import pytest

from nawa_api.ai import embeddings
from nawa_api.ai.embeddings.base import EMBEDDINGS_DIMENSION, EmbeddingsProvider
from nawa_api.ai.embeddings.mock_embeddings import MockEmbeddingsProvider, deterministic_vector
from nawa_api.ai.embeddings.probe import check_embedding_dimension
from nawa_api.runtime.redis import get_redis


def test_mock_vector_is_deterministic_normalized_and_sized():
    a = deterministic_vector("النواة hello", 64)
    b = deterministic_vector("النواة hello", 64)
    assert a == b
    assert len(a) == 64
    assert math.isclose(math.sqrt(sum(x * x for x in a)), 1.0, rel_tol=1e-9)


def test_mock_different_text_gives_different_vector():
    assert deterministic_vector("alpha", 32) != deterministic_vector("beta", 32)


async def test_mock_provider_embeds_batch_to_full_dimension():
    vecs = await MockEmbeddingsProvider().embed_batch(["a", "b"])
    assert len(vecs) == 2
    assert all(len(v) == EMBEDDINGS_DIMENSION for v in vecs)


async def test_embed_requires_the_pii_flag():
    with pytest.raises(TypeError):
        await embeddings.embed(["hello"])  # pii is keyword-only, no default


async def test_embed_empty_returns_empty():
    assert await embeddings.embed([], pii=False) == []


async def test_pii_true_changes_the_embedded_text():
    # With redaction, an email becomes a token, so the vector differs from raw.
    raw = await embeddings.embed(["contact me@x.io"], pii=False)
    redacted = await embeddings.embed(["contact me@x.io"], pii=True)
    assert raw[0] != redacted[0]


async def test_batching_splits_at_ninety_six(monkeypatch):
    seen: list[int] = []

    class Spy(EmbeddingsProvider):
        name = "spy"
        dimension = EMBEDDINGS_DIMENSION

        async def embed_batch(self, texts):
            seen.append(len(texts))
            return [[0.0] * self.dimension for _ in texts]

    monkeypatch.setattr(embeddings, "get_embeddings_provider", lambda name=None: Spy())
    await get_redis().delete(embeddings._QUOTA_KEY)
    out = await embeddings.embed([f"t{i}" for i in range(100)], pii=False)
    assert len(out) == 100
    assert seen == [96, 4]  # two upstream requests
    assert int(await get_redis().get(embeddings._QUOTA_KEY)) == 100


async def test_dimension_probe_matches_live_column(db_session):
    assert await check_embedding_dimension(db_session) is True


async def test_dimension_probe_warns_on_mismatch(db_session, monkeypatch):
    monkeypatch.setattr("nawa_api.ai.embeddings.probe.EMBEDDINGS_DIMENSION", 999)
    assert await check_embedding_dimension(db_session) is False


async def test_dimension_probe_reports_missing_column(db_session, monkeypatch):
    from sqlalchemy import text

    # Point the probe at a column that does not exist → declared is None.
    missing = text(
        "SELECT a.atttypmod FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid "
        "WHERE c.relname = 'resource_chunks' AND a.attname = 'does_not_exist'"
    )
    monkeypatch.setattr("nawa_api.ai.embeddings.probe._ATTTYPMOD_SQL", missing)
    assert await check_embedding_dimension(db_session) is False
