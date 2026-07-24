"""Deterministic, offline, zero-network provider (05-ai-infrastructure.md §3.5).

This is what CI and the entire test suite run against. Same input → same output,
forever, on every machine. It exercises the real pricing path with fake token
counts so cost accounting is covered offline too.
"""

from __future__ import annotations

import json
import re
import types
import typing
from collections.abc import AsyncIterator
from dataclasses import dataclass
from dataclasses import field as dc_field
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

# Verbatim-citation grounding (06-intake-copilot.md §3.1/§5): the fully
# generic `_synthesize` below has no notion of "this quote must actually
# appear in the source text", so any schema requiring a real citation into
# the rendered rubric/application text (ScorecardDraft, HiddenGemReview)
# would always fail `validate_scorecard`/`validate_hidden_gem_review`'s
# truth check under the plain generic synthesis — a real, previously-known
# gap (chunks 4/7/11 documented it, never fixed). Rather than importing
# those two schemas by name (which would couple this generic provider to one
# slice's domain), this detects the shape structurally — a `citations`
# field of models with exactly {source, quote}, and/or a `criteria` field of
# models with a `criterion_key` — and grounds those specific fields in a
# real "answer:<key>" / verbatim substring pulled out of the request's own
# rendered rubric/application-text sections, leaving every other field's
# synthesis (and every other schema entirely) untouched.
_RUBRIC_CRITERION_RE = re.compile(
    r"^- (\S+) \([^)]*\), weight [\d.]+, scale (\d+)-(\d+)", re.MULTILINE
)
_KV_LINE_RE = re.compile(r"^([^\s:][^:\n]*): (.+)$", re.MULTILINE)


@dataclass
class _MockContext:
    rubric_criteria: list[tuple[str, int, int]] = dc_field(default_factory=list)
    answer_kv: list[tuple[str, str]] = dc_field(default_factory=list)


def _build_mock_context(text: str) -> _MockContext:
    rubric_criteria = [
        (key, int(lo), int(hi)) for key, lo, hi in _RUBRIC_CRITERION_RE.findall(text)
    ]
    # Both prompt templates that need grounding render an "Application:\n"
    # section (`score_application`'s comes after the rubric section,
    # `hidden_gem_review`'s is the whole body) — restricting the key:value
    # scan to that section keeps rubric lines (which also contain a colon,
    # before their guidance text) out of the extracted answer key/value pairs.
    _, _, application_section = text.partition("Application:\n")
    # `_application_text()` (jobs/score_applications.py, jobs/hidden_gem_scan.py)
    # appends a trailing "summary: <application.summary>" line that is NOT a
    # key in `original_answers` — a citation naming it as `answer:summary`
    # can never resolve (`_citations._resolve_source` only looks up
    # `original_answers`), so it's excluded here the same way it would need
    # to be excluded by a real, correct citer.
    answer_kv = [
        (key.strip(), value.strip())
        for key, value in _KV_LINE_RE.findall(application_section)
        if key.strip() != "summary"
    ]
    return _MockContext(rubric_criteria=rubric_criteria, answer_kv=answer_kv)


def _is_citation_shaped(model: type) -> bool:
    return isinstance(model, type) and issubclass(model, BaseModel) and (
        set(model.model_fields.keys()) == {"source", "quote"}
    )


def _citation_inner_class(annotation: object) -> type[BaseModel] | None:
    args = typing.get_args(annotation)
    inner = args[0] if args else None
    return inner if _is_citation_shaped(inner) else None


def _grounded_citation(
    citation_cls: type[BaseModel], context: _MockContext, index: int
) -> BaseModel:
    key, value = context.answer_kv[index % len(context.answer_kv)]
    return citation_cls(source=f"answer:{key}", quote=value)


def _grounded_criterion(
    criterion_cls: type[BaseModel],
    key: str,
    scale_max: int,
    fp: str,
    context: _MockContext,
    index: int,
) -> BaseModel:
    base = _synthesize(criterion_cls, f"{key}:{fp}")
    updates: dict[str, object] = {
        "criterion_key": key,
        "score": _seed_int(key, fp) % max(scale_max, 1),
    }
    if "citations" in criterion_cls.model_fields and context.answer_kv:
        citation_cls = _citation_inner_class(criterion_cls.model_fields["citations"].annotation)
        if citation_cls is not None:
            updates["citations"] = [_grounded_citation(citation_cls, context, index)]
    return base.model_copy(update=updates)


def _ground_citations(obj: BaseModel, fp: str, context: _MockContext) -> BaseModel:
    fields = type(obj).model_fields
    if "criteria" in fields and context.rubric_criteria:
        inner = typing.get_args(fields["criteria"].annotation)
        criterion_cls = inner[0] if inner else None
        if criterion_cls is not None and "criterion_key" in criterion_cls.model_fields:
            criteria = [
                _grounded_criterion(criterion_cls, key, scale_max, fp, context, i)
                for i, (key, _lo, scale_max) in enumerate(context.rubric_criteria)
            ]
            return obj.model_copy(update={"criteria": criteria})
    elif "citations" in fields and context.answer_kv:
        citation_cls = _citation_inner_class(fields["citations"].annotation)
        if citation_cls is not None:
            updates: dict[str, object] = {
                "citations": [_grounded_citation(citation_cls, context, 0)]
            }
            # HiddenGemReview-specific but harmless elsewhere: vary the flag by
            # fingerprint instead of the generic always-True bool synthesis,
            # so a demo run doesn't flag literally every reviewed application.
            if "is_hidden_gem" in fields:
                updates["is_hidden_gem"] = int(fp, 16) % 2 == 0
            return obj.model_copy(update=updates)
    return obj

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
        req_text = self._all_text(req)
        # The mock fails one attempt per occurrence of the malformed marker, so a
        # single marker repairs on retry and three markers exhaust the loop.
        fail_attempts = req_text.count("__MOCK_MALFORMED__")
        fp = self._fingerprint(req, schema.__name__)
        context = _build_mock_context(req_text)

        for attempt in range(STRUCTURED_REPAIR_RETRIES + 1):
            if attempt < fail_attempts:
                continue  # malformed payload — would fail validation; run repair
            obj = _ground_citations(_synthesize(schema, fp), fp, context)
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
    for field_name, model_field in schema.model_fields.items():
        values[field_name] = _value_for(model_field.annotation, field_name, fp)
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
