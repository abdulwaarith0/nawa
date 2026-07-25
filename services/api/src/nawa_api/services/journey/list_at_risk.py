"""Cached at-risk progress list for a cohort (07-journey-copilot.md
§2.3/§4.2): overdue (past due_date, not done/waived) or blocked rows, each
carrying a machine-readable reason the board flag and the digest both
render. Key services:journey:list_at_risk:<cohort_id>, TTL 300s. Invalidated
by any progress write in the cohort.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel

from nawa_api.db.journey.list_at_risk_progress_db import list_at_risk_progress_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key

CACHE_TTL_SECONDS = 300


class _CachedList(BaseModel):
    items: list[dict]


def cache_key(*, cohort_id: uuid.UUID) -> str:
    return f"services:journey:list_at_risk:{cohort_id}"


def _reasons(progress, milestone, *, as_of) -> list[str]:
    reasons = []
    if progress.status == "blocked":
        reasons.append(f"blocked:{progress.id}")
    is_overdue = milestone.due_date is not None and milestone.due_date < as_of
    if is_overdue and progress.status != "blocked":
        reasons.append(f"overdue:{milestone.id}")
    return reasons


async def list_at_risk(*, cohort_id: uuid.UUID) -> list[dict]:
    key = cache_key(cohort_id=cohort_id)
    cached = await redis_retrieve_key(key, _CachedList)
    if cached is not None:
        return cached.items

    as_of = datetime.now(UTC).date()
    rows = await list_at_risk_progress_db(cohort_id=cohort_id, as_of=as_of)
    items = [
        {
            "progress_id": str(progress.id),
            "milestone_id": str(milestone.id),
            "founder_profile_id": str(progress.founder_profile_id),
            "status": progress.status,
            "due_date": milestone.due_date.isoformat() if milestone.due_date else None,
            "reasons": _reasons(progress, milestone, as_of=as_of),
        }
        for progress, milestone in rows
    ]
    if items:  # never cache empty
        await redis_update_key(key, _CachedList(items=items), CACHE_TTL_SECONDS)
    return items
