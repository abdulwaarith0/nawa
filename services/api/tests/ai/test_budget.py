import uuid

import pytest

from nawa_api.ai import budget
from nawa_api.contracts.errors import ERR_AI_BUDGET_EXCEEDED, ApiError


def test_is_essential():
    assert budget.is_essential("intake.score") is True
    assert budget.is_essential("intake.hidden_gem") is True
    assert budget.is_essential("assistant.answer") is False


def test_crossed_thresholds_is_pure():
    assert budget.crossed_thresholds(39, 41, 50) == [0.8]  # 40 crossed
    assert budget.crossed_thresholds(49, 51, 50) == [1.0]  # 50 crossed
    assert budget.crossed_thresholds(0, 61, 50) == [0.8, 1.0, 1.2]
    assert budget.crossed_thresholds(41, 44, 50) == []  # no line between


async def test_add_and_get_spend_accumulates():
    cid = uuid.uuid4()
    assert await budget.get_spend(cid) == 0.0
    await budget.add_spend(cid, 10.0)
    total = await budget.add_spend(cid, 5.5)
    assert total == pytest.approx(15.5)
    assert await budget.get_spend(cid) == pytest.approx(15.5)


async def test_no_cycle_means_no_enforcement():
    # Must not raise even when "spend" is irrelevant.
    await budget.enforce_budget(task="intake.score", cycle_id=None, ceiling=1.0)


async def test_non_essential_blocks_at_100_percent():
    cid = uuid.uuid4()
    await budget.add_spend(cid, 100.0)  # exactly the ceiling
    with pytest.raises(ApiError) as exc:
        await budget.enforce_budget(task="assistant.answer", cycle_id=cid, ceiling=100.0)
    assert exc.value is ERR_AI_BUDGET_EXCEEDED
    # Essential scoring still allowed at 100% (its cap is 120%).
    await budget.enforce_budget(task="intake.score", cycle_id=cid, ceiling=100.0)


async def test_essential_blocks_at_120_percent():
    cid = uuid.uuid4()
    await budget.add_spend(cid, 120.0)
    with pytest.raises(ApiError) as exc:
        await budget.enforce_budget(task="intake.score", cycle_id=cid, ceiling=100.0)
    assert exc.value is ERR_AI_BUDGET_EXCEEDED


async def test_below_ceiling_allows_all():
    cid = uuid.uuid4()
    await budget.add_spend(cid, 10.0)
    await budget.enforce_budget(task="assistant.answer", cycle_id=cid, ceiling=100.0)
    await budget.enforce_budget(task="intake.score", cycle_id=cid, ceiling=100.0)
