from decimal import Decimal

from nawa_api.ai.pricing import estimate_cost_usd


def test_input_output_priced_per_million():
    # 1M input tokens on opus (5.00/MTok in), no output.
    assert estimate_cost_usd("claude-opus-4-8", tokens_in=1_000_000, tokens_out=0) == Decimal(
        "5.000000"
    )
    # 1M output tokens (25.00/MTok out).
    assert estimate_cost_usd("claude-opus-4-8", tokens_in=0, tokens_out=1_000_000) == Decimal(
        "25.000000"
    )


def test_cached_input_bills_at_cache_read_rate():
    # All input cached → cache_read rate (0.50/MTok), uncached input is 0.
    cost = estimate_cost_usd(
        "claude-opus-4-8", tokens_in=1_000_000, tokens_out=0, tokens_cached=1_000_000
    )
    assert cost == Decimal("0.500000")


def test_partial_cache_splits_input():
    # 1M input, 250k cached → 750k @5.00 + 250k @0.50 = 3.75 + 0.125 = 3.875
    cost = estimate_cost_usd(
        "claude-opus-4-8", tokens_in=1_000_000, tokens_out=0, tokens_cached=250_000
    )
    assert cost == Decimal("3.875000")


def test_unknown_model_is_zero_not_error():
    assert estimate_cost_usd("gpt-unknown", tokens_in=1000, tokens_out=1000) == Decimal("0.000000")


def test_result_is_quantized_to_six_places():
    cost = estimate_cost_usd("claude-haiku-4-5", tokens_in=123, tokens_out=45)
    assert cost.as_tuple().exponent == -6
