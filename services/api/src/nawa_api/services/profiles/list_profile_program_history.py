"""Cached program history for a founder profile: every cohort membership,
newest first, with its program/cycle names — the "which programs am I in"
list the journey frontend uses to route a founder to their timeline.

Key services:profiles:list_profile_program_history:<profile_id>, TTL 600s.
Invalidated by cohort-acceptance writes — intake's decide_application.py
already fires this exact glob on `accept` decisions (built ahead of this
service existing, per its own comment).
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from nawa_api.db.profiles.list_profile_program_history_db import (
    list_profile_program_history_db,
)
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key

CACHE_TTL_SECONDS = 600


class _CachedList(BaseModel):
    items: list[dict]


def cache_key(*, profile_id: uuid.UUID) -> str:
    return f"services:profiles:list_profile_program_history:{profile_id}"


def _dto(row: dict) -> dict:
    program, cycle, cohort, membership = (
        row["program"],
        row["cycle"],
        row["cohort"],
        row["membership"],
    )
    return {
        "cohort_id": str(cohort.id),
        "cohort_name_ar": cohort.name_ar,
        "cohort_name_en": cohort.name_en,
        "cycle_id": str(cycle.id),
        "cycle_name_ar": cycle.name_ar,
        "cycle_name_en": cycle.name_en,
        "program_id": str(program.id),
        "program_name_ar": program.name_ar,
        "program_name_en": program.name_en,
        "role": membership.role,
        "status": membership.status,
        "starts_at": cohort.starts_at.isoformat(),
    }


async def list_profile_program_history(*, profile_id: uuid.UUID) -> list[dict]:
    key = cache_key(profile_id=profile_id)
    cached = await redis_retrieve_key(key, _CachedList)
    if cached is not None:
        return cached.items
    rows = await list_profile_program_history_db(profile_id=profile_id)
    items = [_dto(row) for row in rows]
    if items:  # never cache empty
        await redis_update_key(key, _CachedList(items=items), CACHE_TTL_SECONDS)
    return items
