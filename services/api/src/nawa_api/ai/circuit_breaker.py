"""Per-provider circuit breaker (05-ai-infrastructure.md §8.3).

State lives in Redis (ai:cb:<provider>). CLOSED → OPEN after
CB_FAILURE_THRESHOLD consecutive timeout/5xx/connection failures (the gateway
decides what counts — refusals and validation errors do NOT). OPEN denies for
CB_COOLDOWN_SECONDS, then HALF-OPEN admits one probe: success closes it, failure
re-opens. Transitions log a WARNING and bump a Prometheus counter.
"""

from __future__ import annotations

import time

from nawa_api.metrics.registry import get_or_create_counter
from nawa_api.runtime.redis import get_redis
from nawa_api.utils.logger import get_logger

CB_FAILURE_THRESHOLD = 5
CB_COOLDOWN_SECONDS = 60

STATE_CLOSED = "closed"
STATE_OPEN = "open"
STATE_HALF_OPEN = "half_open"

_transitions = get_or_create_counter(
    "nawa_ai_circuit_breaker_transitions_total",
    "AI circuit-breaker state transitions",
    ["provider", "to_state"],
)


def _key(provider: str) -> str:
    return f"ai:cb:{provider}"


async def state(provider: str) -> str:
    data = await get_redis().hgetall(_key(provider))
    return data.get("state", STATE_CLOSED) if data else STATE_CLOSED


async def allow(provider: str) -> bool:
    """True when a request may proceed. An OPEN breaker past its cooldown flips
    to HALF-OPEN and admits the probe."""
    data = await get_redis().hgetall(_key(provider))
    if not data or data.get("state", STATE_CLOSED) != STATE_OPEN:
        return True
    opened_at = float(data.get("opened_at", 0.0))
    if time.time() - opened_at >= CB_COOLDOWN_SECONDS:
        await _transition(provider, STATE_HALF_OPEN)
        return True
    return False


async def record_success(provider: str) -> None:
    was = await state(provider)
    await get_redis().hset(_key(provider), mapping={"state": STATE_CLOSED, "failures": 0})
    if was != STATE_CLOSED:
        _transitions.labels(provider=provider, to_state=STATE_CLOSED).inc()


async def record_failure(provider: str) -> None:
    redis = get_redis()
    was = await state(provider)
    failures = await redis.hincrby(_key(provider), "failures", 1)
    # A failed HALF-OPEN probe re-opens immediately; otherwise open at threshold.
    if was == STATE_HALF_OPEN or failures >= CB_FAILURE_THRESHOLD:
        await _open(provider)


async def _open(provider: str) -> None:
    await get_redis().hset(_key(provider), mapping={"state": STATE_OPEN, "opened_at": time.time()})
    _transitions.labels(provider=provider, to_state=STATE_OPEN).inc()
    get_logger().warning("ai_circuit_breaker_open", provider=provider)


async def _transition(provider: str, to_state: str) -> None:
    await get_redis().hset(_key(provider), mapping={"state": to_state})
    _transitions.labels(provider=provider, to_state=to_state).inc()


async def reset(provider: str) -> None:
    """Test/ops helper — clear a provider's breaker state."""
    await get_redis().delete(_key(provider))
