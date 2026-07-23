from decimal import Decimal

import pytest
from pydantic import BaseModel

from nawa_api.ai.providers._structured import complete_structured_with_repair
from nawa_api.ai.types import LLMResponse
from nawa_api.contracts.errors import ERR_AI_MALFORMED_OUTPUT, ApiError


class M(BaseModel):
    x: int


def _resp() -> LLMResponse:
    return LLMResponse(
        text="",
        input_tokens=1,
        output_tokens=1,
        model="m",
        provider="p",
        stop_reason="end_turn",
        latency_ms=1,
        cost_estimate=Decimal("0"),
    )


async def test_returns_on_first_valid():
    async def attempt(repair):
        return '{"x": 5}', _resp()

    obj, _ = await complete_structured_with_repair(M, attempt)
    assert obj.x == 5


async def test_repairs_after_one_bad(monkeypatch):
    seen: list[list[dict]] = []

    async def attempt(repair):
        seen.append(repair)
        return ('{"x": "bad"}' if len(seen) == 1 else '{"x": 9}'), _resp()

    obj, _ = await complete_structured_with_repair(M, attempt)
    assert obj.x == 9
    assert len(seen) == 2
    assert seen[1] and seen[1][0]["role"] == "assistant"  # repair turn appended


async def test_gives_up_after_budget():
    async def attempt(repair):
        return '{"x": "still bad"}', _resp()

    with pytest.raises(ApiError) as exc:
        await complete_structured_with_repair(M, attempt)
    assert exc.value is ERR_AI_MALFORMED_OUTPUT
