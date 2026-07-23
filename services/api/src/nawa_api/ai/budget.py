"""Per-cycle AI budget counters (05-ai-infrastructure.md §8.2).

Spend accrues in Redis via INCRBYFLOAT keyed by cycle + month. Enforcement runs
before the provider call; accrual + threshold signalling run after. Human-facing
scoring is "essential" and continues to a 120% hard stop; non-essential tasks
(digests, matching) block at 100%. The Redis counter is operational state, not a
response cache — the ai_calls ledger is the reconcilable record of spend.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from nawa_api.contracts.errors import ERR_AI_BUDGET_EXCEEDED
from nawa_api.runtime.redis import get_redis
from nawa_api.runtime.settings import get_settings

# Human-facing tasks that must not be cut off at 100% — they run to the 120% cap.
ESSENTIAL_TASKS = frozenset({"intake.score", "intake.hidden_gem"})

NON_ESSENTIAL_CEILING = 1.0
ESSENTIAL_CEILING = 1.2
THRESHOLDS = (0.8, 1.0, 1.2)


def is_essential(task: str) -> bool:
    return task in ESSENTIAL_TASKS


def budget_key(cycle_id: uuid.UUID) -> str:
    month = datetime.now(UTC).strftime("%Y-%m")
    return f"ai:budget:{cycle_id}:{month}"


async def get_spend(cycle_id: uuid.UUID) -> float:
    raw = await get_redis().get(budget_key(cycle_id))
    return float(raw) if raw else 0.0


async def add_spend(cycle_id: uuid.UUID, cost: Decimal | float) -> float:
    return float(await get_redis().incrbyfloat(budget_key(cycle_id), float(cost)))


def crossed_thresholds(prev: float, new: float, ceiling: float) -> list[float]:
    """Which of the 0.8/1.0/1.2 lines the accrual newly crossed (pure)."""
    return [p for p in THRESHOLDS if prev < ceiling * p <= new]


async def enforce_budget(
    *, task: str, cycle_id: uuid.UUID | None, ceiling: float | None = None
) -> None:
    """Raise ERR_AI_BUDGET_EXCEEDED when the cycle's spend has hit this task's
    ceiling. No cycle attribution → no budget enforcement."""
    if cycle_id is None:
        return
    limit = ceiling if ceiling is not None else get_settings().ai_cycle_budget_usd
    cap = limit * (ESSENTIAL_CEILING if is_essential(task) else NON_ESSENTIAL_CEILING)
    if await get_spend(cycle_id) >= cap:
        raise ERR_AI_BUDGET_EXCEEDED
