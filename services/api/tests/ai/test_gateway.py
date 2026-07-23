import uuid

import pytest
import pytest_asyncio
from pydantic import BaseModel

from nawa_api.ai import budget, gateway
from nawa_api.ai import circuit_breaker as cb
from nawa_api.ai.pii import PiiMapping
from nawa_api.ai.types import LLMRequest, Tier
from nawa_api.contracts.errors import (
    ERR_AI_BUDGET_EXCEEDED,
    ERR_AI_MALFORMED_OUTPUT,
    ERR_AI_REFUSED,
    ERR_AI_TIMEOUT,
    ERR_AI_UNAVAILABLE,
    ERR_RATE_LIMITED,
    ApiError,
)
from nawa_api.runtime.redis import get_redis
from nawa_api.services.rate_limit.consume import RateLimitResult


class Out(BaseModel):
    a: str
    b: int


def _req(content: str = "hello", task: str = "assistant.answer", tier: Tier = Tier.LARGE):
    return LLMRequest(
        task=task,
        prompt_version="v1",
        tier=tier,
        system="sys",
        messages=[{"role": "user", "content": content}],
    )


@pytest_asyncio.fixture(autouse=True)
async def _clean_redis():
    # Isolate rate / breaker / budget state between gateway tests.
    redis = get_redis()
    for pattern in ("rl:ai:*", "ai:cb:mock", "ai:budget:*"):
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
    yield


@pytest.fixture
def calls(monkeypatch):
    captured: list[dict] = []

    async def fake(**kwargs):
        captured.append(kwargs)
        return None

    monkeypatch.setattr(gateway, "create_ai_call_db", fake)
    return captured


async def test_complete_happy_path_logs_ok_with_cost(calls):
    resp = await gateway.complete(_req(), pii_safe=True, created_by=uuid.uuid4())
    assert resp.text.startswith("[mock:")
    assert resp.cost_estimate > 0
    assert len(calls) == 1
    row = calls[0]
    assert row["status"] == "ok"
    assert row["error_code"] is None
    assert row["cost_estimate"] > 0
    assert row["prompt_hash"]
    assert row["provider"] == "mock"


async def test_complete_structured_happy_path(calls):
    obj, resp = await gateway.complete_structured(_req(), Out, pii_safe=True)
    assert isinstance(obj, Out)
    assert resp.cost_estimate > 0
    assert calls[0]["status"] == "ok"


async def test_requires_pii_flag_or_subject():
    with pytest.raises(ValueError):
        await gateway.complete(_req())


async def test_structured_malformed_logs_error(calls):
    req = _req(content="__MOCK_MALFORMED__ __MOCK_MALFORMED__ __MOCK_MALFORMED__")
    with pytest.raises(ApiError) as exc:
        await gateway.complete_structured(req, Out, pii_safe=True)
    assert exc.value is ERR_AI_MALFORMED_OUTPUT
    assert calls[0]["status"] == "error"
    assert calls[0]["error_code"] == "malformed"


async def test_refusal_does_not_count_toward_breaker(calls):
    with pytest.raises(ApiError) as exc:
        await gateway.complete(_req("__MOCK_REFUSAL__"), pii_safe=True)
    assert exc.value is ERR_AI_REFUSED
    assert calls[0]["error_code"] == "refusal"
    assert await cb.state("mock") == cb.STATE_CLOSED


async def test_timeout_logs_error_and_counts_one_breaker_failure(calls):
    with pytest.raises(ApiError) as exc:
        await gateway.complete(_req("__MOCK_TIMEOUT__"), pii_safe=True)
    assert exc.value is ERR_AI_TIMEOUT
    assert calls[0]["status"] == "error"
    assert calls[0]["error_code"] == "timeout"
    data = await get_redis().hgetall(cb._key("mock"))
    assert int(data["failures"]) == 1


async def test_open_breaker_fails_closed_without_logging(calls):
    for _ in range(cb.CB_FAILURE_THRESHOLD):
        await cb.record_failure("mock")
    with pytest.raises(ApiError) as exc:
        await gateway.complete(_req(), pii_safe=True)
    assert exc.value is ERR_AI_UNAVAILABLE
    assert calls == []  # rejected before any provider call


async def test_budget_blocks_non_essential_before_provider(calls):
    cid = uuid.uuid4()
    await budget.add_spend(cid, 10_000.0)  # far over any ceiling
    with pytest.raises(ApiError) as exc:
        await gateway.complete(_req(task="assistant.answer"), pii_safe=True, cycle_id=cid)
    assert exc.value is ERR_AI_BUDGET_EXCEEDED
    assert calls == []


async def test_subject_pseudonymizes_and_persists(monkeypatch, calls):
    persisted: dict = {}

    async def fake_get(**_kwargs):
        return PiiMapping(tokens={})

    async def fake_upsert(*, subject_type, subject_id, mapping):
        persisted["mapping"] = mapping
        return mapping

    monkeypatch.setattr(gateway, "get_pii_mapping", fake_get)
    monkeypatch.setattr(gateway, "upsert_pii_mapping", fake_upsert)

    sid = uuid.uuid4()
    await gateway.complete(
        _req(content="email me@x.io"), subject=("application", sid), created_by=uuid.uuid4()
    )
    assert any(t.startswith("EMAIL_") for t in persisted["mapping"].tokens)
    assert calls[0]["subject_type"] == "application"
    assert calls[0]["subject_id"] == sid


async def test_stream_yields_events_and_logs(calls):
    events = [e async for e in gateway.stream(_req(), pii_safe=True)]
    assert any(e.type == "done" for e in events)
    assert any(e.type == "delta" for e in events)
    assert calls[0]["status"] == "ok"


def _limiter(blocked_scope: str):
    async def fake(*, scope, identifier, limit, window_seconds=60):
        return RateLimitResult(
            allowed=scope != blocked_scope, limit=limit, remaining=0, reset_seconds=1
        )

    return fake


async def test_user_rate_limit_blocks(monkeypatch, calls):
    monkeypatch.setattr(gateway, "consume", _limiter("ai:user"))
    with pytest.raises(ApiError) as exc:
        await gateway.complete(_req(), pii_safe=True, created_by=uuid.uuid4())
    assert exc.value is ERR_RATE_LIMITED
    assert calls == []


async def test_global_rate_limit_blocks(monkeypatch, calls):
    monkeypatch.setattr(gateway, "consume", _limiter("ai:global"))
    # created_by=None (batch job) still hits the global net.
    with pytest.raises(ApiError) as exc:
        await gateway.complete(_req(), pii_safe=True, created_by=None)
    assert exc.value is ERR_RATE_LIMITED


async def test_complete_accrues_budget_on_success(calls):
    cid = uuid.uuid4()
    resp = await gateway.complete(_req(), pii_safe=True, cycle_id=cid)
    assert await budget.get_spend(cid) == pytest.approx(float(resp.cost_estimate))


async def test_structured_subject_rehydrates(monkeypatch, calls):
    async def fake_get(**_kwargs):
        return PiiMapping(tokens={})

    async def fake_upsert(*, subject_type, subject_id, mapping):
        return mapping

    monkeypatch.setattr(gateway, "get_pii_mapping", fake_get)
    monkeypatch.setattr(gateway, "upsert_pii_mapping", fake_upsert)
    obj, _ = await gateway.complete_structured(
        _req(content="me@x.io"), Out, subject=("application", uuid.uuid4())
    )
    assert isinstance(obj, Out)


async def test_stream_with_subject_and_cycle(monkeypatch, calls):
    async def fake_get(**_kwargs):
        return PiiMapping(tokens={})

    async def fake_upsert(*, subject_type, subject_id, mapping):
        return mapping

    monkeypatch.setattr(gateway, "get_pii_mapping", fake_get)
    monkeypatch.setattr(gateway, "upsert_pii_mapping", fake_upsert)
    cid = uuid.uuid4()
    events = [
        e
        async for e in gateway.stream(
            _req(content="me@x.io"), subject=("application", uuid.uuid4()), cycle_id=cid
        )
    ]
    assert any(e.type == "done" for e in events)
    assert calls[0]["status"] == "ok"
