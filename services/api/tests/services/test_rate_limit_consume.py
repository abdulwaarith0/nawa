import uuid

import pytest

from nawa_api.services.rate_limit.consume import consume


@pytest.mark.asyncio
async def test_consume_allows_up_to_limit_then_blocks():
    ident = f"test-{uuid.uuid4()}"
    results = [await consume(scope="test", identifier=ident, limit=3) for _ in range(4)]
    assert [r.allowed for r in results] == [True, True, True, False]
    assert results[-1].remaining == 0


@pytest.mark.asyncio
async def test_consume_reports_remaining_and_reset():
    ident = f"test-{uuid.uuid4()}"
    first = await consume(scope="test", identifier=ident, limit=5, window_seconds=60)
    assert first.allowed is True
    assert first.limit == 5
    assert first.remaining == 4
    assert first.reset_seconds > 0
