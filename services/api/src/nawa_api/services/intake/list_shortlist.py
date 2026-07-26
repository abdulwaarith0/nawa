"""Cached, filterable shortlist read (06-intake-copilot.md §6.1).

Key services:intake:list_shortlist:<canonical-param-hash>, TTL 300s.
Invalidated by scoring, hidden-gem, dedup, decision, and rubric writes (every
write names its globs — canon). Ranked by ai_total_score desc against the
cycle's CURRENT active rubric version; every filter is combinable.
"""

from __future__ import annotations

import json
import uuid
from hashlib import sha256

from pydantic import BaseModel

from nawa_api.contracts.errors import ERR_NOT_FOUND
from nawa_api.db.intake.get_active_rubric_db import get_active_rubric_db
from nawa_api.db.intake.list_pending_dedup_matches_for_applications_db import (
    list_pending_dedup_matches_for_applications_db,
)
from nawa_api.db.intake.list_scorecard_criteria_db import list_scorecard_criteria_db
from nawa_api.db.intake.list_shortlist_db import list_shortlist_db
from nawa_api.db.programs.get_program_cycle_db import get_program_cycle_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key

CACHE_TTL_SECONDS = 300
_KEY_PREFIX = "services:intake:list_shortlist"
_VALID_FLAGS = frozenset({"hidden_gem", "dedup_pending", "normalize_failed"})
_VALID_DECISIONS = frozenset({"undecided", "shortlist", "waitlist", "reject", "accept"})


class _ShortlistPage(BaseModel):
    items: list[dict]


def _parse_score_band(score_band: str | None) -> tuple[float | None, float | None]:
    if score_band is None:
        return None, None
    lo, _, hi = score_band.partition("-")
    return float(lo), float(hi)


def cache_key(
    *,
    cycle_id: uuid.UUID,
    score_band: str | None,
    criterion: str | None,
    criterion_min: float | None,
    flags: frozenset[str],
    language: str | None,
    country: str | None,
    decision: str | None,
    q: str | None,
    limit: int,
    offset: int,
) -> str:
    raw = json.dumps(
        {
            "cycle_id": str(cycle_id),
            "score_band": score_band or "*",
            "criterion": criterion or "*",
            "criterion_min": criterion_min if criterion_min is not None else "*",
            "flags": sorted(flags) or "*",
            "language": language or "*",
            "country": country or "*",
            "decision": decision or "*",
            "q": q or "*",
            "limit": limit,
            "offset": offset,
        },
        sort_keys=True,
    )
    return f"{_KEY_PREFIX}:{sha256(raw.encode()).hexdigest()[:24]}"


async def list_shortlist(
    *,
    cycle_id: uuid.UUID,
    score_band: str | None = None,
    criterion: str | None = None,
    criterion_min: float | None = None,
    flags: frozenset[str] = frozenset(),
    language: str | None = None,
    country: str | None = None,
    decision: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    flags = frozenset(flags) & _VALID_FLAGS
    if decision is not None and decision not in _VALID_DECISIONS:
        decision = None

    key = cache_key(
        cycle_id=cycle_id,
        score_band=score_band,
        criterion=criterion,
        criterion_min=criterion_min,
        flags=flags,
        language=language,
        country=country,
        decision=decision,
        q=q,
        limit=limit,
        offset=offset,
    )
    cached = await redis_retrieve_key(key, _ShortlistPage)
    if cached is not None:
        return cached.items

    cycle = await get_program_cycle_db(cycle_id=cycle_id)
    if cycle is None:
        raise ERR_NOT_FOUND
    rubric = await get_active_rubric_db(program_id=cycle.program_id)
    if rubric is None:
        return []

    score_min, score_max = _parse_score_band(score_band)
    rows = await list_shortlist_db(
        cycle_id=cycle_id,
        rubric_id=rubric.id,
        score_min=score_min,
        score_max=score_max,
        criterion=criterion,
        criterion_min=criterion_min,
        flags=flags,
        language=language,
        country=country,
        decision=decision,
        q=q,
        limit=limit,
        offset=offset,
    )
    items = await _build_items(rows, offset=offset)
    if items:  # never cache empty
        await redis_update_key(key, _ShortlistPage(items=items), CACHE_TTL_SECONDS)
    return items


async def _build_items(rows, *, offset: int) -> list[dict]:
    scorecard_ids = [scorecard.id for _app, scorecard, _decision in rows if scorecard is not None]
    criteria_rows = await list_scorecard_criteria_db(scorecard_ids=scorecard_ids)
    criteria_by_scorecard: dict[uuid.UUID, list[dict]] = {}
    for criterion_row in criteria_rows:
        criteria_by_scorecard.setdefault(criterion_row.scorecard_id, []).append(
            {
                "criterion_key": criterion_row.criterion_key,
                "score": criterion_row.score,
                "weight": criterion_row.weight,
            }
        )

    application_ids = [application.id for application, _s, _d in rows]
    pending_matches = await list_pending_dedup_matches_for_applications_db(
        application_ids=application_ids
    )
    dedup_pending_ids: set[uuid.UUID] = set()
    for match in pending_matches:
        dedup_pending_ids.add(match.application_id)
        dedup_pending_ids.add(match.matched_application_id)

    items = []
    for index, (application, scorecard, latest_decision) in enumerate(rows):
        items.append(
            {
                "rank": offset + index + 1,
                "application_id": str(application.id),
                "applicant_name": application.applicant_name,
                "title": application.title,
                "language": application.source_language,
                "country": application.normalized.get("country"),
                "domain": application.normalized.get("field"),
                "total_score": application.ai_total_score,
                "criteria": criteria_by_scorecard.get(scorecard.id, []) if scorecard else [],
                "hidden_gem": scorecard.hidden_gem if scorecard else False,
                "dedup_pending": application.id in dedup_pending_ids,
                "normalize_failed": application.status == "normalize_failed",
                "status": application.status,
                "decision": _decision_state(application.status, latest_decision),
            }
        )
    return items


def _decision_state(status: str, latest_decision: str | None) -> str:
    if status == "shortlisted":
        return "shortlist"
    if status == "waitlisted":
        return "waitlist"
    if status == "decided":
        return latest_decision or "decided"
    return "undecided"
