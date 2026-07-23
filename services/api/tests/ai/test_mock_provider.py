from decimal import Decimal
from typing import Literal

import pytest
from pydantic import BaseModel

from nawa_api.ai.providers.mock_provider import MockLLMProvider
from nawa_api.ai.types import DeltaEvent, DoneEvent, LLMRequest, Tier
from nawa_api.contracts.errors import (
    ERR_AI_MALFORMED_OUTPUT,
    ERR_AI_REFUSED,
    ERR_AI_TIMEOUT,
    ApiError,
)


class Inner(BaseModel):
    label: str
    weight: float


class Sample(BaseModel):
    name: str
    score: int
    ratio: Decimal
    ok: bool
    tier: Tier
    tags: list[str]
    nested: Inner
    note: str | None
    kind: Literal["a", "b"]


def _req(content: str = "hello", tier: Tier = Tier.SMALL) -> LLMRequest:
    return LLMRequest(
        task="intake.score",
        prompt_version="v1",
        tier=tier,
        system="You are a scorer.",
        messages=[{"role": "user", "content": content}],
    )


async def test_complete_is_deterministic_with_nonzero_cost():
    mock = MockLLMProvider()
    a = await mock.complete(_req())
    b = await mock.complete(_req())
    assert a == b
    assert a.text.startswith("[mock:intake.score:")
    assert a.input_tokens > 0 and a.output_tokens > 0
    assert a.cost_estimate > Decimal(0)
    assert a.provider == "mock"
    assert a.model == "claude-haiku-4-5"


async def test_large_tier_resolves_to_opus():
    mock = MockLLMProvider()
    resp = await mock.complete(_req(tier=Tier.LARGE))
    assert resp.model == "claude-opus-4-8"


async def test_timeout_marker_raises():
    with pytest.raises(ApiError) as exc:
        await MockLLMProvider().complete(_req("please __MOCK_TIMEOUT__ now"))
    assert exc.value is ERR_AI_TIMEOUT


async def test_refusal_marker_raises():
    with pytest.raises(ApiError) as exc:
        await MockLLMProvider().complete(_req("__MOCK_REFUSAL__"))
    assert exc.value is ERR_AI_REFUSED


async def test_structured_happy_path_returns_valid_instance():
    obj, resp = await MockLLMProvider().complete_structured(_req(), Sample)
    assert isinstance(obj, Sample)
    assert obj.tier == Tier.SMALL  # first enum member
    assert obj.kind == "a"  # first literal
    assert len(obj.tags) == 1
    assert isinstance(obj.nested, Inner)
    assert obj.note is not None  # Optional resolves to the inner type
    assert resp.cost_estimate > Decimal(0)


async def test_structured_repairs_after_one_malformed():
    obj, _ = await MockLLMProvider().complete_structured(_req("__MOCK_MALFORMED__"), Sample)
    assert isinstance(obj, Sample)


async def test_structured_gives_up_after_repair_budget():
    # Three malformed attempts exhaust the 1 + 2 repair budget.
    req = _req("__MOCK_MALFORMED__ __MOCK_MALFORMED__ __MOCK_MALFORMED__")
    with pytest.raises(ApiError) as exc:
        await MockLLMProvider().complete_structured(req, Sample)
    assert exc.value is ERR_AI_MALFORMED_OUTPUT


async def test_stream_yields_three_deltas_then_done():
    mock = MockLLMProvider()
    events = [e async for e in mock.stream(_req())]
    deltas = [e for e in events if isinstance(e, DeltaEvent)]
    done = [e for e in events if isinstance(e, DoneEvent)]
    assert len(done) == 1
    assert "".join(d.text for d in deltas) == done[0].response.text


async def test_ratelimit_marker_raises():
    from nawa_api.contracts.errors import ERR_RATE_LIMITED

    with pytest.raises(ApiError) as exc:
        await MockLLMProvider().complete(_req("__MOCK_RATELIMIT__"))
    assert exc.value is ERR_RATE_LIMITED


class Weird(BaseModel):
    meta: dict
    anything: object


async def test_synthesize_handles_dict_and_unknown_types():
    obj, _ = await MockLLMProvider().complete_structured(_req(), Weird)
    assert obj.meta == {}
    assert isinstance(obj.anything, str)


async def test_fixture_response_is_used_when_present():
    from nawa_api.ai.providers import mock_provider

    mock = MockLLMProvider()
    req = _req(content="fixture-me")
    fp = mock._fingerprint(req)
    task_dir = mock_provider._FIXTURE_ROOT / req.task
    task_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = task_dir / f"{fp}.json"
    fixture_path.write_text('{"text": "canned answer"}', encoding="utf-8")
    try:
        resp = await mock.complete(req)
        assert resp.text == "canned answer"
    finally:
        fixture_path.unlink()
