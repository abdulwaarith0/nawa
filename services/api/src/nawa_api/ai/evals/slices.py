"""Per-demographic-slice agreement + bias gap (05-ai-infrastructure.md §10).

The concrete mechanism behind "bias reviewed per demographic slice": a max
inter-slice agreement gap above BIAS_GAP_THRESHOLD points raises a warning.
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel

from nawa_api.ai.evals.agreement import top_quartile_agreement
from nawa_api.ai.evals.schemas import ScoredEntry

BIAS_GAP_THRESHOLD = 15.0


class SliceResult(BaseModel):
    per_slice: dict[str, float]
    max_gap: float
    biased: bool


def compute_slice_agreements(
    entries: list[ScoredEntry],
    human: list[float],
    ai: list[float],
    *,
    key: Callable[[ScoredEntry], str],
) -> SliceResult:
    groups: dict[str, list[int]] = {}
    for index, entry in enumerate(entries):
        groups.setdefault(key(entry), []).append(index)

    per_slice = {
        name: top_quartile_agreement([human[i] for i in idxs], [ai[i] for i in idxs])
        for name, idxs in groups.items()
    }
    values = list(per_slice.values())
    gap = (max(values) - min(values)) if len(values) >= 2 else 0.0
    return SliceResult(per_slice=per_slice, max_gap=gap, biased=gap > BIAS_GAP_THRESHOLD)
