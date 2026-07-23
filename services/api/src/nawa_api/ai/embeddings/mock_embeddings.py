"""Deterministic, offline embeddings (05-ai-infrastructure.md §4).

A hash-derived, L2-normalized vector per text. Similar texts do NOT get similar
vectors — it is a hash, not a semantic model. Tests that need controlled
similarity insert fixture vectors directly; the mock exists so pipelines run
offline, not to fake semantics.
"""

from __future__ import annotations

import math
from hashlib import sha256

from nawa_api.ai.embeddings.base import EMBEDDINGS_DIMENSION, EmbeddingsProvider


def deterministic_vector(text: str, dimension: int = EMBEDDINGS_DIMENSION) -> list[float]:
    raw = bytearray()
    counter = 0
    while len(raw) < dimension:
        raw.extend(sha256(f"{counter}:{text}".encode()).digest())
        counter += 1
    vals = [(byte / 127.5) - 1.0 for byte in raw[:dimension]]  # each in [-1, 1)
    norm = math.sqrt(sum(v * v for v in vals)) or 1.0
    return [v / norm for v in vals]


class MockEmbeddingsProvider(EmbeddingsProvider):
    name = "mock"
    dimension = EMBEDDINGS_DIMENSION

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [deterministic_vector(t, self.dimension) for t in texts]
