import time
import uuid

from nawa_api.ai import circuit_breaker as cb
from nawa_api.runtime.redis import get_redis


def _provider() -> str:
    return f"test-{uuid.uuid4().hex[:8]}"


async def test_starts_closed_and_allows():
    p = _provider()
    assert await cb.state(p) == cb.STATE_CLOSED
    assert await cb.allow(p) is True


async def test_below_threshold_stays_closed():
    p = _provider()
    for _ in range(cb.CB_FAILURE_THRESHOLD - 1):
        await cb.record_failure(p)
    assert await cb.state(p) == cb.STATE_CLOSED
    assert await cb.allow(p) is True


async def test_opens_after_threshold_failures_and_denies():
    p = _provider()
    for _ in range(cb.CB_FAILURE_THRESHOLD):
        await cb.record_failure(p)
    assert await cb.state(p) == cb.STATE_OPEN
    assert await cb.allow(p) is False  # inside cooldown


async def test_success_closes_an_open_breaker():
    p = _provider()
    for _ in range(cb.CB_FAILURE_THRESHOLD):
        await cb.record_failure(p)
    await cb.record_success(p)
    assert await cb.state(p) == cb.STATE_CLOSED
    assert await cb.allow(p) is True


async def test_cooldown_flips_to_half_open_then_closes():
    p = _provider()
    for _ in range(cb.CB_FAILURE_THRESHOLD):
        await cb.record_failure(p)
    # Simulate the cooldown having elapsed.
    await get_redis().hset(cb._key(p), "opened_at", time.time() - cb.CB_COOLDOWN_SECONDS - 1)
    assert await cb.allow(p) is True  # admits a probe
    assert await cb.state(p) == cb.STATE_HALF_OPEN
    await cb.record_success(p)
    assert await cb.state(p) == cb.STATE_CLOSED


async def test_half_open_failure_reopens_immediately():
    p = _provider()
    for _ in range(cb.CB_FAILURE_THRESHOLD):
        await cb.record_failure(p)
    await get_redis().hset(cb._key(p), "opened_at", time.time() - cb.CB_COOLDOWN_SECONDS - 1)
    await cb.allow(p)  # -> half_open
    await cb.record_failure(p)  # probe fails
    assert await cb.state(p) == cb.STATE_OPEN


async def test_reset_clears_state():
    p = _provider()
    await cb.record_failure(p)
    await cb.reset(p)
    assert await cb.state(p) == cb.STATE_CLOSED
