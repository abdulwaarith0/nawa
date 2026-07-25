"""Fan the cohort's program templates into cohort-scoped milestones + a
not_started progress row per active member (07-journey-copilot.md §2.1).
Idempotent (fill-gaps) — safe to call again for a late-joining member or a
template added after the first run.

Invalidates every cache surface the fan-out can affect: cohort milestones,
board, member timelines, and at-risk (all cohort-scoped, so a glob).
"""

from __future__ import annotations

import uuid

from nawa_api.contracts.errors import ERR_NOT_FOUND
from nawa_api.db.cohorts.get_cohort_db import get_cohort_db
from nawa_api.db.journey.instantiate_cohort_milestones_db import (
    instantiate_cohort_milestones_db,
)
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys
from nawa_api.utils.publish_event import publish_event

_INVALIDATION_GLOBS = (
    "services:journey:list_cohort_milestones:*",
    "services:journey:get_cohort_board:*",
    "services:journey:get_member_timeline:*",
    "services:journey:list_at_risk:*",
)


async def instantiate_cohort_milestones(*, cohort_id: uuid.UUID) -> dict:
    cohort = await get_cohort_db(cohort_id=cohort_id)
    if cohort is None:
        raise ERR_NOT_FOUND
    result = await instantiate_cohort_milestones_db(cohort_id=cohort_id)
    await invalidate_cache_keys(*_INVALIDATION_GLOBS)
    await publish_event(
        f"events:journey:{cohort_id}",
        {"type": "journey.milestones.instantiated", "cohort_id": str(cohort_id)},
    )
    return result
