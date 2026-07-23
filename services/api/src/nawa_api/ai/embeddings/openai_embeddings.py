"""OpenAI embeddings backend — the ONLY openai-embeddings import (§4).

Entirely `# pragma: no cover`: it requires the openai SDK and a live key, so CI
(offline, mock-only) never executes it.
"""

from __future__ import annotations

from nawa_api.ai.embeddings.base import EmbeddingsProvider
from nawa_api.contracts.errors import ERR_AI_NOT_CONFIGURED
from nawa_api.runtime.settings import get_settings


class OpenAIEmbeddingsProvider(EmbeddingsProvider):  # pragma: no cover - needs SDK + key
    name = "openai"
    dimension = 1536
    _MODEL = "text-embedding-3-small"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ERR_AI_NOT_CONFIGURED
        import openai

        self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(model=self._MODEL, input=texts)
        return [item.embedding for item in resp.data]
