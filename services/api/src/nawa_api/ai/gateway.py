"""The AI gateway (05-ai-infrastructure.md §1 public entry points).

complete() / complete_structured() / stream() are the ONLY way feature code
reaches a model. This single choke point enforces, in order: the PII contract,
rate limits, per-cycle budget, pseudonymization, provider selection with the
circuit breaker, bounded retry with a timeout, response rehydration, the
ai_calls ledger row (fire-and-forget), and budget accrual. No feature module
imports a vendor SDK — that boundary is what makes the AI posture enforceable.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from decimal import Decimal
from hashlib import sha256

from pydantic import BaseModel

from nawa_api.ai import budget
from nawa_api.ai import circuit_breaker as cb
from nawa_api.ai.pii import KnownEntities, PiiMapping, pseudonymize, rehydrate
from nawa_api.ai.providers import get_provider
from nawa_api.ai.providers.base import LLMProvider
from nawa_api.ai.types import LLMRequest, LLMResponse, StreamEvent
from nawa_api.contracts.errors import (
    ERR_AI_MALFORMED_OUTPUT,
    ERR_AI_REFUSED,
    ERR_AI_TIMEOUT,
    ERR_AI_TRUNCATED,
    ERR_AI_UNAVAILABLE,
    ERR_RATE_LIMITED,
    ApiError,
)
from nawa_api.db.ai_calls.create_ai_call_db import create_ai_call_db
from nawa_api.runtime.settings import get_settings
from nawa_api.services.pii.get_pii_mapping import get_pii_mapping
from nawa_api.services.pii.upsert_pii_mapping import upsert_pii_mapping
from nawa_api.services.rate_limit.consume import consume
from nawa_api.utils.logger import get_logger

AI_TIMEOUT_SECONDS = 120
AI_MAX_RETRIES = 3
_USER_LIMIT_PER_MIN = 30
_GLOBAL_LIMIT_PER_MIN = 300

# Only availability failures are retried and count toward the breaker; a refusal
# or malformed output is the provider working correctly.
_RETRYABLE: frozenset[ApiError] = frozenset({ERR_AI_TIMEOUT, ERR_AI_UNAVAILABLE})

_ERROR_CODES: dict[ApiError, str] = {
    ERR_AI_REFUSED: "refusal",
    ERR_AI_TIMEOUT: "timeout",
    ERR_AI_MALFORMED_OUTPUT: "malformed",
    ERR_RATE_LIMITED: "rate_limited",
    ERR_AI_TRUNCATED: "provider_error",
    ERR_AI_UNAVAILABLE: "provider_error",
}

Subject = tuple[str, uuid.UUID]


def _error_code(exc: ApiError) -> str:
    return _ERROR_CODES.get(exc, "provider_error")


def _assert_pii_contract(*, pii_safe: bool, subject: Subject | None) -> None:
    if not pii_safe and subject is None:
        raise ValueError(
            "gateway call must pass pii_safe=True (institutional content) or a "
            "subject=(subject_type, subject_id) so PII is pseudonymized"
        )


async def _check_rate(created_by: uuid.UUID | None) -> None:
    # Interactive callers are per-user limited; arq jobs (created_by=None) bypass
    # the per-user limit but still respect the global safety net.
    if created_by is not None:
        user = await consume(
            scope="ai:user", identifier=str(created_by), limit=_USER_LIMIT_PER_MIN
        )
        if not user.allowed:
            raise ERR_RATE_LIMITED
    glob = await consume(scope="ai:global", identifier="all", limit=_GLOBAL_LIMIT_PER_MIN)
    if not glob.allowed:
        raise ERR_RATE_LIMITED


async def _pseudonymize_request(
    request: LLMRequest, *, subject: Subject | None, pii_safe: bool
) -> tuple[LLMRequest, PiiMapping | None]:
    if pii_safe or subject is None:
        return request, None
    subject_type, subject_id = subject
    mapping = await get_pii_mapping(subject_type=subject_type, subject_id=subject_id)
    new_messages: list[dict] = []
    for message in request.messages:
        content = str(message.get("content", ""))
        redacted, mapping = pseudonymize(content, KnownEntities(), prior=mapping)
        new_messages.append({**message, "content": redacted})
    await upsert_pii_mapping(
        subject_type=subject_type, subject_id=subject_id, mapping=mapping
    )
    return request.model_copy(update={"messages": new_messages}), mapping


def _prompt_hash(request: LLMRequest) -> str:
    """sha256 of the exact rendered prompt AFTER pseudonymization (03's semantics)."""
    body = request.system + "\n" + "\n".join(str(m.get("content", "")) for m in request.messages)
    return sha256(body.encode("utf-8")).hexdigest()


async def _select_provider(name: str | None) -> LLMProvider:
    provider = get_provider(name)
    if await cb.allow(provider.name):
        return provider
    # Breaker OPEN. A configured, healthy fallback would be tried here; none is
    # wired yet, so fail closed.
    raise ERR_AI_UNAVAILABLE


async def _invoke[T](provider: LLMProvider, call: Callable[[], Awaitable[T]]) -> T:
    """Run one provider call with a timeout + bounded retry on availability
    failures. Records exactly one breaker outcome per gateway call."""
    settings = get_settings()
    last: ApiError = ERR_AI_UNAVAILABLE
    for attempt in range(AI_MAX_RETRIES + 1):
        try:
            async with asyncio.timeout(AI_TIMEOUT_SECONDS):
                result = await call()
            await cb.record_success(provider.name)
            return result
        except ApiError as exc:
            if exc not in _RETRYABLE:
                raise  # refusal/malformed/etc — no retry, no breaker failure
            last = exc
        except TimeoutError:  # pragma: no cover - real asyncio timeout, offline mock never hits
            last = ERR_AI_TIMEOUT
        if settings.environment != "test" and attempt < AI_MAX_RETRIES:  # pragma: no cover
            await asyncio.sleep(min(2**attempt, 20))
    await cb.record_failure(provider.name)
    raise last


async def _write_ai_call(**kwargs: object) -> None:
    # Fire-and-forget: a logging failure must never fail the user's request.
    try:
        await create_ai_call_db(**kwargs)  # type: ignore[arg-type]
    except Exception:
        get_logger().warning("ai_calls_write_failed", exc_info=True)


async def _accrue(task: str, cycle_id: uuid.UUID | None, cost: Decimal) -> None:
    if cycle_id is None:
        return
    ceiling = get_settings().ai_cycle_budget_usd
    new_total = await budget.add_spend(cycle_id, cost)
    for pct in budget.crossed_thresholds(new_total - float(cost), new_total, ceiling):
        get_logger().warning(
            "ai_budget_threshold", cycle_id=str(cycle_id), pct=pct, spent_usd=new_total
        )


def _rehydrate_response(resp: LLMResponse, mapping: PiiMapping | None) -> LLMResponse:
    if mapping is None:
        return resp
    return resp.model_copy(update={"text": rehydrate(resp.text, mapping)})


async def complete(
    request: LLMRequest,
    *,
    subject: Subject | None = None,
    pii_safe: bool = False,
    created_by: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
    provider_name: str | None = None,
) -> LLMResponse:
    _assert_pii_contract(pii_safe=pii_safe, subject=subject)
    await _check_rate(created_by)
    await budget.enforce_budget(task=request.task, cycle_id=cycle_id)

    pseudo, mapping = await _pseudonymize_request(request, subject=subject, pii_safe=pii_safe)
    prompt_hash = _prompt_hash(pseudo)
    provider = await _select_provider(provider_name)
    model = provider.resolve_model(request.tier)

    loop = asyncio.get_event_loop()
    start = loop.time()
    status, error_code, resp = "error", "provider_error", None
    try:
        resp = await _invoke(provider, lambda: provider.complete(pseudo))
        status, error_code = "ok", None
        return _rehydrate_response(resp, mapping)
    except ApiError as exc:
        error_code = _error_code(exc)
        raise
    finally:
        latency_ms = int((loop.time() - start) * 1000)
        await _write_ai_call(
            task=request.task,
            provider=provider.name,
            model=model,
            prompt_hash=prompt_hash,
            prompt_version=request.prompt_version,
            tier=request.tier.value,
            tokens_in=resp.input_tokens if resp else 0,
            tokens_out=resp.output_tokens if resp else 0,
            tokens_cached=resp.cached_tokens if resp else 0,
            cost_estimate=float(resp.cost_estimate) if resp else 0.0,
            latency_ms=latency_ms,
            status=status,
            error_code=error_code,
            request_id=resp.request_id if resp else None,
            cycle_id=cycle_id,
            created_by=created_by,
            subject_type=subject[0] if subject else None,
            subject_id=subject[1] if subject else None,
        )
        if resp is not None and status == "ok":
            await _accrue(request.task, cycle_id, resp.cost_estimate)


async def complete_structured(
    request: LLMRequest,
    schema: type[BaseModel],
    *,
    subject: Subject | None = None,
    pii_safe: bool = False,
    created_by: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
    provider_name: str | None = None,
) -> tuple[BaseModel, LLMResponse]:
    _assert_pii_contract(pii_safe=pii_safe, subject=subject)
    await _check_rate(created_by)
    await budget.enforce_budget(task=request.task, cycle_id=cycle_id)

    pseudo, mapping = await _pseudonymize_request(request, subject=subject, pii_safe=pii_safe)
    prompt_hash = _prompt_hash(pseudo)
    provider = await _select_provider(provider_name)
    model = provider.resolve_model(request.tier)

    loop = asyncio.get_event_loop()
    start = loop.time()
    status, error_code, resp = "error", "provider_error", None
    try:
        obj, resp = await _invoke(
            provider, lambda: provider.complete_structured(pseudo, schema)
        )
        status, error_code = "ok", None
        if mapping is not None:
            # Rehydrate every string leaf via a JSON round-trip.
            obj = schema.model_validate_json(rehydrate(obj.model_dump_json(), mapping))
            resp = _rehydrate_response(resp, mapping)
        return obj, resp
    except ApiError as exc:
        error_code = _error_code(exc)
        raise
    finally:
        latency_ms = int((loop.time() - start) * 1000)
        await _write_ai_call(
            task=request.task,
            provider=provider.name,
            model=model,
            prompt_hash=prompt_hash,
            prompt_version=request.prompt_version,
            tier=request.tier.value,
            tokens_in=resp.input_tokens if resp else 0,
            tokens_out=resp.output_tokens if resp else 0,
            tokens_cached=resp.cached_tokens if resp else 0,
            cost_estimate=float(resp.cost_estimate) if resp else 0.0,
            latency_ms=latency_ms,
            status=status,
            error_code=error_code,
            request_id=resp.request_id if resp else None,
            cycle_id=cycle_id,
            created_by=created_by,
            subject_type=subject[0] if subject else None,
            subject_id=subject[1] if subject else None,
        )
        if resp is not None and status == "ok":
            await _accrue(request.task, cycle_id, resp.cost_estimate)


async def stream(
    request: LLMRequest,
    *,
    subject: Subject | None = None,
    pii_safe: bool = False,
    created_by: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
    provider_name: str | None = None,
) -> AsyncIterator[StreamEvent]:
    _assert_pii_contract(pii_safe=pii_safe, subject=subject)
    await _check_rate(created_by)
    await budget.enforce_budget(task=request.task, cycle_id=cycle_id)

    pseudo, mapping = await _pseudonymize_request(request, subject=subject, pii_safe=pii_safe)
    prompt_hash = _prompt_hash(pseudo)
    provider = await _select_provider(provider_name)
    model = provider.resolve_model(request.tier)

    final: LLMResponse | None = None
    async for event in provider.stream(pseudo):
        if event.type == "delta" and mapping is not None:
            event = event.model_copy(update={"text": rehydrate(event.text, mapping)})
        if event.type == "done":
            final = _rehydrate_response(event.response, mapping)
            event = event.model_copy(update={"response": final})
        yield event

    await cb.record_success(provider.name)
    await _write_ai_call(
        task=request.task,
        provider=provider.name,
        model=model,
        prompt_hash=prompt_hash,
        prompt_version=request.prompt_version,
        tier=request.tier.value,
        tokens_in=final.input_tokens if final else 0,
        tokens_out=final.output_tokens if final else 0,
        cost_estimate=float(final.cost_estimate) if final else 0.0,
        status="ok",
        request_id=final.request_id if final else None,
        cycle_id=cycle_id,
        created_by=created_by,
        subject_type=subject[0] if subject else None,
        subject_id=subject[1] if subject else None,
    )
    if final is not None:
        await _accrue(request.task, cycle_id, final.cost_estimate)
