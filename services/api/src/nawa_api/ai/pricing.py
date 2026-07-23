"""Per-model USD pricing and cost estimation (05-ai-infrastructure.md §7).

Prices in USD per million tokens. These change — re-verify against the vendors'
published pricing whenever a model id in providers/ changes. Last verified:
2026-07-23 (from 05-ai-infrastructure.md §7's table).

OpenAI chat/embedding model prices are filled from env-configured ids at deploy
time and are intentionally absent here; an unknown model yields cost 0 plus a
WARNING (never crash a call over a missing price row).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from nawa_api.utils.logger import get_logger

_MILLION = Decimal(1_000_000)
_CENTS = Decimal("0.000001")  # 6 decimal places, matching ai_calls.cost_estimate

PRICING: dict[str, dict[str, Decimal]] = {
    "claude-opus-4-8": {
        "in": Decimal("5.00"),
        "out": Decimal("25.00"),
        "cache_read": Decimal("0.50"),
    },
    "claude-haiku-4-5": {
        "in": Decimal("1.00"),
        "out": Decimal("5.00"),
        "cache_read": Decimal("0.10"),
    },
}


def estimate_cost_usd(
    model: str,
    *,
    tokens_in: int,
    tokens_out: int,
    tokens_cached: int = 0,
) -> Decimal:
    """USD cost for a call, quantized to 6 dp. Cached input tokens bill at the
    cache-read rate; the remaining (uncached) input tokens bill at the input
    rate. Unknown model → 0 with a WARNING, never an exception."""
    row = PRICING.get(model)
    if row is None:
        get_logger().warning("pricing_unknown_model", model=model)
        return Decimal("0.000000")

    uncached_in = max(tokens_in - tokens_cached, 0)
    cost = (
        Decimal(uncached_in) * row["in"]
        + Decimal(tokens_cached) * row["cache_read"]
        + Decimal(tokens_out) * row["out"]
    ) / _MILLION
    return cost.quantize(_CENTS, rounding=ROUND_HALF_UP)
