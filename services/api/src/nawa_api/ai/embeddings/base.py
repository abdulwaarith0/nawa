"""EmbeddingsProvider abstraction (05-ai-infrastructure.md §4).

Anthropic ships no embeddings endpoint, so the default embeddings backend is a
different vendor from the default chat provider — the abstraction makes that
unremarkable. EMBEDDINGS_DIMENSION is the single source of truth for the vector
width: the Alembic migrations declare `vector(EMBEDDINGS_DIMENSION)`, and a boot
probe checks the live column matches. Changing it is a *migration*, not a config
flip.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from nawa_api.runtime.settings import get_settings

EMBEDDINGS_DIMENSION = get_settings().embeddings_dimension
EMBED_BATCH_SIZE = 96
EMBED_RATE_PER_MIN = 3000


class EmbeddingsProvider(ABC):
    name: str
    dimension: int  # class attribute — migrations and the boot probe read it

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
