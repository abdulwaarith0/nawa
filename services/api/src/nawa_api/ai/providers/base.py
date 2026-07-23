"""LLMProvider abstract base (05-ai-infrastructure.md §3).

Concrete adapters live beside this file and are the ONLY modules permitted to
import a vendor SDK. Everything else goes through ai/gateway.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from pydantic import BaseModel

from nawa_api.ai.types import LLMRequest, LLMResponse, StreamEvent, Tier


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def complete(self, req: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    async def complete_structured(
        self, req: LLMRequest, schema: type[BaseModel]
    ) -> tuple[BaseModel, LLMResponse]: ...

    @abstractmethod
    def stream(self, req: LLMRequest) -> AsyncIterator[StreamEvent]: ...

    @abstractmethod
    def resolve_model(self, tier: Tier) -> str: ...
