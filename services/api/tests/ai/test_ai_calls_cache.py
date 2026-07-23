import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from nawa_api.runtime.redis import get_redis
from nawa_api.services.ai_calls import list_ai_calls as mod
from nawa_api.services.ai_calls.list_ai_calls import get_query_key, list_ai_calls


def _row():
    return SimpleNamespace(
        id=uuid.uuid4(),
        task="intake.score",
        provider="mock",
        model="claude-opus-4-8",
        tier="large",
        status="ok",
        error_code=None,
        tokens_in=10,
        tokens_out=5,
        tokens_cached=0,
        cost_estimate=Decimal("0.01"),
        latency_ms=3,
        request_id="r",
        cycle_id=None,
        created_by=None,
        subject_type=None,
        subject_id=None,
        created_at=datetime.now(UTC),
    )


async def test_result_is_cached_and_reused(monkeypatch):
    calls: list[dict] = []

    async def fake_db(**kwargs):
        calls.append(kwargs)
        return [_row()]

    monkeypatch.setattr(mod, "list_ai_calls_db", fake_db)
    task = f"t-{uuid.uuid4()}"
    await get_redis().delete(
        get_query_key(task=task, provider=None, status=None, cycle=None, limit=100)
    )
    first = await list_ai_calls(task=task)
    second = await list_ai_calls(task=task)
    assert len(calls) == 1  # second served from cache
    assert first == second


async def test_empty_result_is_not_cached(monkeypatch):
    calls: list[int] = []

    async def fake_db(**kwargs):
        calls.append(1)
        return []

    monkeypatch.setattr(mod, "list_ai_calls_db", fake_db)
    task = f"empty-{uuid.uuid4()}"
    await list_ai_calls(task=task)
    await list_ai_calls(task=task)
    assert len(calls) == 2  # empty never cached
