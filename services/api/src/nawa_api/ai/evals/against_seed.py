"""`--against-seed` (06-intake-copilot.md §8): a second, database-grounded
truth alongside the checked-in fixtures. Checks the seeded demo data's
ACTUAL hidden-gem flags and dedup matches against the answer key the seed
script writes to `site_config["seed:ground_truth"]` — never synthetic
stand-ins. Best-effort: if the demo pipeline (upload -> score ->
hidden_gem_scan -> dedup_scan) hasn't actually been run yet, the
corresponding scorecards/dedup_matches simply won't exist and the counts
come back 0/N — this is a diagnostic, not a hard gate on the eval's exit
code.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from nawa_api.ai.evals.schemas import GroundTruth
from nawa_api.db.intake.list_dedup_matches_db import list_dedup_matches_db
from nawa_api.db.intake.list_scorecards_for_application_db import (
    list_scorecards_for_application_db,
)


class SeedCheckResult(BaseModel):
    hidden_gem_recall_pct: float
    hidden_gem_checked: int
    dedup_recovered_pct: float
    dedup_checked: int


def _parse_uuid(raw: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


async def _hidden_gem_recall(hidden_gem_ids: list[str]) -> tuple[int, int]:
    hits = total = 0
    for raw_id in hidden_gem_ids:
        application_id = _parse_uuid(raw_id)
        if application_id is None:
            continue
        total += 1
        scorecards = await list_scorecards_for_application_db(application_id=application_id)
        if any(sc.source == "ai" and sc.hidden_gem for sc in scorecards):
            hits += 1
    return hits, total


async def _dedup_recovery(dedup_pair_ids: list[list[str]]) -> tuple[int, int]:
    hits = total = 0
    for pair in dedup_pair_ids:
        if len(pair) != 2:
            continue
        a, b = _parse_uuid(pair[0]), _parse_uuid(pair[1])
        if a is None or b is None:
            continue
        total += 1
        matches = await list_dedup_matches_db(application_id=a)
        if any({m.application_id, m.matched_application_id} == {a, b} for m in matches):
            hits += 1
    return hits, total


async def check_against_seed(ground_truth: GroundTruth) -> SeedCheckResult:
    gem_hits, gem_total = await _hidden_gem_recall(ground_truth.hidden_gem_ids)
    dedup_hits, dedup_total = await _dedup_recovery(ground_truth.dedup_pair_ids)
    return SeedCheckResult(
        hidden_gem_recall_pct=(gem_hits / gem_total * 100) if gem_total else 0.0,
        hidden_gem_checked=gem_total,
        dedup_recovered_pct=(dedup_hits / dedup_total * 100) if dedup_total else 0.0,
        dedup_checked=dedup_total,
    )


def format_seed_check(result: SeedCheckResult) -> str:
    return (
        f"SEED CHECK: hidden-gem recall {result.hidden_gem_recall_pct:.1f}% "
        f"({result.hidden_gem_checked} checked) | "
        f"dedup recovered {result.dedup_recovered_pct:.1f}% ({result.dedup_checked} checked)"
    )
