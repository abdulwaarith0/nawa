"""Core AI gateway types (05-ai-infrastructure.md §2).

Everything crossing the gateway boundary is one of these Pydantic models. No
vendor SDK type ever leaks past ai/providers/.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Tier(StrEnum):
    SMALL = "small"  # fast/cheap: classification, language detection, extraction
    LARGE = "large"  # reasoning: scoring, hidden-gem analysis, report drafting


class LLMRequest(BaseModel):
    task: str  # dot-namespaced task id per 03's ai_calls.task vocabulary
    prompt_version: str  # from the registry, never free-typed
    tier: Tier
    system: str
    messages: list[dict]  # already-pseudonymized content ONLY
    max_tokens: int = 4096
    stop_sequences: list[str] | None = None
    metadata: dict = Field(default_factory=dict)  # cycle_id/application_id — never PII


class LLMResponse(BaseModel):
    text: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    model: str
    provider: str
    stop_reason: str  # "end_turn" | "max_tokens" | "refusal" | ...
    latency_ms: int
    cost_estimate: Decimal  # USD — same name as 03's ai_calls.cost_estimate column
    request_id: str | None = None


class DeltaEvent(BaseModel):
    type: Literal["delta"] = "delta"
    text: str


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    response: LLMResponse


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: str


StreamEvent = DeltaEvent | DoneEvent | ErrorEvent
