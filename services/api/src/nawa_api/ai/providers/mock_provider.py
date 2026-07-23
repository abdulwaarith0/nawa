"""Deterministic, offline, zero-network provider (05-ai-infrastructure.md §3.5).

This is what CI and the entire test suite run against. Same input → same output,
forever, on every machine. It exercises the real pricing path with fake token
counts so cost accounting is covered offline too.
"""

from __future__ import annotations

import json
import types
import typing
from collections.abc import AsyncIterator
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel

from nawa_api.ai.pricing import estimate_cost_usd
from nawa_api.ai.providers.base import LLMProvider
from nawa_api.ai.types import DeltaEvent, DoneEvent, LLMRequest, LLMResponse, StreamEvent, Tier
from nawa_api.contracts.errors import (
    ERR_AI_MALFORMED_OUTPUT,
    ERR_AI_REFUSED,
    ERR_AI_TIMEOUT,
    ERR_RATE_LIMITED,
)

STRUCTURED_REPAIR_RETRIES = 2

# Fixtures live in the checked-in test tree. mock_provider.py is at
# .../services/api/src/nawa_api/ai/providers/mock_provider.py — five parents up
# is services/api, then tests/ai/fixtures.
_FIXTURE_ROOT = Path(__file__).resolve().parents[4] / "tests" / "ai" / "fixtures"

# The mock impersonates the default provider's models so pricing yields a
# nonzero cost (the ai_calls ledger must show real cost fields offline).
_TIER_MODEL = {Tier.SMALL: "claude-haiku-4-5", Tier.LARGE: "claude-opus-4-8"}


class MockLLMProvider(LLMProvider):
    name = "mock"

    def resolve_model(self, tier: Tier) -> str:
        return _TIER_MODEL[tier]

    # --- determinism helpers ------------------------------------------------
    def _fingerprint(self, req: LLMRequest, schema_name: str | None = None) -> str:
        payload = {
            "task": req.task,
            "prompt_version": req.prompt_version,
            "system": req.system,
            "messages": req.messages,
            "schema_name": schema_name,
        }
        canon = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(canon.encode("utf-8")).hexdigest()[:16]

    def _all_text(self, req: LLMRequest) -> str:
        parts = [req.system]
        parts.extend(str(m.get("content", "")) for m in req.messages)
        return "\n".join(parts)

    def _tokens(self, fp: str) -> tuple[int, int]:
        # Deterministic, always nonzero.
        tin = int(fp[:4], 16) % 500 + 100
        tout = int(fp[4:8], 16) % 300 + 50
        return tin, tout

    def _load_fixture(self, task: str, fp: str) -> dict | None:
        path = _FIXTURE_ROOT / task / f"{fp}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _check_markers(self, req: LLMRequest) -> None:
        text = self._all_text(req)
        if "__MOCK_TIMEOUT__" in text:
            raise ERR_AI_TIMEOUT
        if "__MOCK_RATELIMIT__" in text:
            raise ERR_RATE_LIMITED
        if "__MOCK_REFUSAL__" in text:
            raise ERR_AI_REFUSED

    def _response(self, *, text: str, model: str, fp: str) -> LLMResponse:
        tin, tout = self._tokens(fp)
        return LLMResponse(
            text=text,
            input_tokens=tin,
            output_tokens=tout,
            cached_tokens=0,
            model=model,
            provider=self.name,
            stop_reason="end_turn",
            latency_ms=1,
            cost_estimate=estimate_cost_usd(model, tokens_in=tin, tokens_out=tout),
            request_id=f"mock-{fp}",
        )

    # --- LLMProvider surface ------------------------------------------------
    async def complete(self, req: LLMRequest) -> LLMResponse:
        self._check_markers(req)
        model = self.resolve_model(req.tier)
        fp = self._fingerprint(req)
        fixture = self._load_fixture(req.task, fp)
        text = fixture["text"] if fixture and "text" in fixture else f"[mock:{req.task}:{fp}]"
        return self._response(text=text, model=model, fp=fp)

    async def complete_structured(
        self, req: LLMRequest, schema: type[BaseModel]
    ) -> tuple[BaseModel, LLMResponse]:
        self._check_markers(req)
        model = self.resolve_model(req.tier)
        # The mock fails one attempt per occurrence of the malformed marker, so a
        # single marker repairs on retry and three markers exhaust the loop.
        fail_attempts = self._all_text(req).count("__MOCK_MALFORMED__")
        fp = self._fingerprint(req, schema.__name__)

        for attempt in range(STRUCTURED_REPAIR_RETRIES + 1):
            if attempt < fail_attempts:
                continue  # malformed payload — would fail validation; run repair
            obj = _synthesize(schema, fp)
            return obj, self._response(text=obj.model_dump_json(), model=model, fp=fp)

        raise ERR_AI_MALFORMED_OUTPUT

    async def stream(self, req: LLMRequest) -> AsyncIterator[StreamEvent]:
        self._check_markers(req)
        resp = await self.complete(req)
        text = resp.text
        n = 3
        size = max(1, -(-len(text) // n))  # ceil division
        chunks = [text[i : i + size] for i in range(0, len(text), size)] or [""]
        for chunk in chunks:
            yield DeltaEvent(text=chunk)
        yield DoneEvent(response=resp)


def _synthesize(schema: type[BaseModel], fp: str) -> BaseModel:
    """Build a schema-valid instance with deterministic values seeded from fp."""
    values: dict[str, object] = {}
    for field_name, field in schema.model_fields.items():
        values[field_name] = _value_for(field.annotation, field_name, fp)
    return schema(**values)


def _seed_int(field_name: str, fp: str) -> int:
    return int(sha256(f"{field_name}:{fp}".encode()).hexdigest()[:8], 16)


def _value_for(anno: object, field_name: str, fp: str) -> object:
    origin = typing.get_origin(anno)
    args = typing.get_args(anno)

    # Optional / Union — pick the first non-None member.
    if origin in (typing.Union, types.UnionType):
        non_none = [a for a in args if a is not type(None)]
        return _value_for(non_none[0], field_name, fp) if non_none else None

    if origin is typing.Literal:
        return args[0]

    if origin in (list, list):
        inner = args[0] if args else str
        return [_value_for(inner, field_name, fp)]

    if origin in (dict,):
        return {}

    if isinstance(anno, type):
        if anno is dict:
            return {}
        if anno is list:
            return []
        if issubclass(anno, BaseModel):
            return _synthesize(anno, f"{field_name}:{fp}")
        if issubclass(anno, Enum):
            return next(iter(anno))
        if anno is bool:
            return True
        if anno is int:
            return _seed_int(field_name, fp) % 1000
        if anno is float:
            return (_seed_int(field_name, fp) % 1000) / 10.0
        if anno is Decimal:
            return Decimal(_seed_int(field_name, fp) % 1000)
        if anno is str:
            return f"{field_name}:{fp[:8]}"

    return f"{field_name}:{fp[:8]}"
