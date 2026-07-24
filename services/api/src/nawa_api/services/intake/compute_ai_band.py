"""AI recommendation band (06-intake-copilot.md §6.2) — pure, no DB, no
gateway. "top-N-by-capacity -> shortlist recommendation, next band ->
waitlist, else reject." Rank is 1-based (competition ranking: ties share a
rank). This band is a recommendation for the override-reason rule, never a
decision — a human always decides.
"""

from __future__ import annotations

DEFAULT_SHORTLIST_CAPACITY = 20
DEFAULT_WAITLIST_CAPACITY = 20


def resolve_capacities(*, program_config: dict, cycle_config: dict) -> tuple[int, int]:
    """Cycle's own `intake` config overrides the program's, key by key — the
    per-cycle override jsonb 06-intake-copilot.md §1 describes for rubric
    selection applies the same way here. No capacity configured anywhere ->
    a documented default, not a silent guess at cycle size."""
    merged = {**program_config.get("intake", {}), **cycle_config.get("intake", {})}
    shortlist_capacity = merged.get("shortlist_capacity", DEFAULT_SHORTLIST_CAPACITY)
    waitlist_capacity = merged.get("waitlist_capacity", DEFAULT_WAITLIST_CAPACITY)
    return shortlist_capacity, waitlist_capacity


def compute_ai_band(*, rank: int, shortlist_capacity: int, waitlist_capacity: int) -> str:
    if rank <= shortlist_capacity:
        return "shortlist"
    if rank <= shortlist_capacity + waitlist_capacity:
        return "waitlist"
    return "reject"
