import math

from nawa_api.runtime.settings import get_settings
from nawa_api.seed_data.embeddings import (
    deterministic_vector,
    near_duplicate_vector,
    source_hash,
)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb)


def test_deterministic_vector_is_reproducible():
    v1 = deterministic_vector("application-1")
    v2 = deterministic_vector("application-1")
    assert v1 == v2


def test_deterministic_vector_has_configured_dimension():
    v = deterministic_vector("application-1")
    assert len(v) == get_settings().embeddings_dimension


def test_deterministic_vector_is_l2_normalized():
    v = deterministic_vector("application-1")
    norm = math.sqrt(sum(x * x for x in v))
    assert abs(norm - 1.0) < 1e-6


def test_different_keys_produce_different_vectors():
    v1 = deterministic_vector("application-1")
    v2 = deterministic_vector("application-2")
    assert v1 != v2


def test_near_duplicate_vector_lands_high_similarity():
    base = deterministic_vector("planted-pair-a")
    dup = near_duplicate_vector(base, noise_key="planted-pair-b")
    similarity = _cosine(base, dup)
    assert similarity >= 0.85


def test_unrelated_vectors_land_low_similarity():
    a = deterministic_vector("unrelated-a")
    b = deterministic_vector("unrelated-b")
    similarity = _cosine(a, b)
    assert similarity < 0.3


def test_source_hash_is_deterministic_and_content_sensitive():
    assert source_hash("content-a") == source_hash("content-a")
    assert source_hash("content-a") != source_hash("content-b")
