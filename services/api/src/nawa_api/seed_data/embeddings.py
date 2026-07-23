"""Deterministic pseudo-embeddings for the seed script.

Real embeddings arrive with 05-ai-infrastructure.md's gateway; the seed never
calls an external API. Vectors are seeded by a content hash so identical
content always produces the same vector, and `source_hash` makes the future
swap-out automatic. Duplicate/near-duplicate pairs are generated as one
vector plus a small perturbation so cosine similarity lands high, letting
HNSW k-NN queries genuinely recover the planted pairs.
"""

import hashlib
import random

from nawa_api.runtime.settings import get_settings

_DIM = get_settings().embeddings_dimension
_MODEL_NAME = "seed-deterministic-v1"


def _seed_from(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = sum(v * v for v in vec) ** 0.5
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def deterministic_vector(content_key: str) -> list[float]:
    rng = random.Random(_seed_from(content_key))
    vec = [rng.gauss(0, 1) for _ in range(_DIM)]
    return _l2_normalize(vec)


def near_duplicate_vector(
    base_vector: list[float], *, noise_key: str, noise_scale: float = 0.012
) -> list[float]:
    """Partner's vector plus small per-dimension noise so cosine similarity
    lands ~0.9+ even at high dimensionality (empirically tuned: at 1536 dims,
    noise_scale=0.012 -> cosine ~0.90; 0.008 -> ~0.95)."""
    rng = random.Random(_seed_from(noise_key))
    noisy = [v + rng.gauss(0, noise_scale) for v in base_vector]
    return _l2_normalize(noisy)


def source_hash(content_key: str) -> str:
    return hashlib.sha256(content_key.encode("utf-8")).hexdigest()


EMBEDDING_MODEL = _MODEL_NAME
