from nawa_api.services.intake.compute_ai_band import compute_ai_band, resolve_capacities


def test_top_ranks_are_shortlist():
    assert compute_ai_band(rank=1, shortlist_capacity=20, waitlist_capacity=20) == "shortlist"
    assert compute_ai_band(rank=20, shortlist_capacity=20, waitlist_capacity=20) == "shortlist"


def test_next_band_is_waitlist():
    assert compute_ai_band(rank=21, shortlist_capacity=20, waitlist_capacity=20) == "waitlist"
    assert compute_ai_band(rank=40, shortlist_capacity=20, waitlist_capacity=20) == "waitlist"


def test_beyond_both_bands_is_reject():
    assert compute_ai_band(rank=41, shortlist_capacity=20, waitlist_capacity=20) == "reject"


def test_zero_capacity_means_everyone_is_rejected():
    assert compute_ai_band(rank=1, shortlist_capacity=0, waitlist_capacity=0) == "reject"


def test_resolve_capacities_uses_defaults_when_unconfigured():
    shortlist_cap, waitlist_cap = resolve_capacities(program_config={}, cycle_config={})
    assert shortlist_cap == 20
    assert waitlist_cap == 20


def test_resolve_capacities_program_config_is_used():
    shortlist_cap, waitlist_cap = resolve_capacities(
        program_config={"intake": {"shortlist_capacity": 5, "waitlist_capacity": 10}},
        cycle_config={},
    )
    assert (shortlist_cap, waitlist_cap) == (5, 10)


def test_resolve_capacities_cycle_config_overrides_program_per_key():
    shortlist_cap, waitlist_cap = resolve_capacities(
        program_config={"intake": {"shortlist_capacity": 5, "waitlist_capacity": 10}},
        cycle_config={"intake": {"shortlist_capacity": 30}},  # only overrides one key
    )
    assert (shortlist_cap, waitlist_cap) == (30, 10)
