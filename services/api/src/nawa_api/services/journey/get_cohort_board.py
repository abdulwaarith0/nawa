"""Cached program-manager board grid (07-journey-copilot.md §2.1/§2.3):
milestones as columns, active members as rows, one cell per pair carrying
the member's progress status and an overdue flag (past due_date, not
done/waived — the same rule `list_at_risk` uses for the board flag).

Key services:journey:get_cohort_board:<cohort_id>, TTL 300s. Invalidated by
any progress/milestone write in the cohort.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel

from nawa_api.db.journey.get_cohort_board_db import get_cohort_board_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key

CACHE_TTL_SECONDS = 300
_NOT_OVERDUE_STATUSES = frozenset({"done", "waived"})


class _CachedBoard(BaseModel):
    milestones: list[dict]
    members: list[dict]
    cells: list[dict]


def cache_key(*, cohort_id: uuid.UUID) -> str:
    return f"services:journey:get_cohort_board:{cohort_id}"


def _is_overdue(*, due_date, status: str, as_of) -> bool:
    return due_date is not None and due_date < as_of and status not in _NOT_OVERDUE_STATUSES


async def get_cohort_board(*, cohort_id: uuid.UUID) -> dict:
    key = cache_key(cohort_id=cohort_id)
    cached = await redis_retrieve_key(key, _CachedBoard)
    if cached is not None:
        return cached.model_dump()

    raw = await get_cohort_board_db(cohort_id=cohort_id)
    as_of = datetime.now(UTC).date()

    milestones = [
        {
            "id": str(m.id),
            "sequence": m.sequence,
            "title_ar": m.title_ar,
            "title_en": m.title_en,
            "due_date": m.due_date.isoformat() if m.due_date else None,
            "evidence_required": m.evidence_required,
        }
        for m in raw["milestones"]
    ]
    milestones_by_id = {m.id: m for m in raw["milestones"]}

    members = [
        {
            "cohort_member_id": str(cohort_member.id),
            "founder_profile_id": str(profile.id),
            "display_name_ar": profile.display_name_ar,
            "display_name_en": profile.display_name_en,
            "handle": profile.handle,
        }
        for cohort_member, profile in raw["members"]
    ]

    cells = [
        {
            "milestone_id": str(p.milestone_id),
            "cohort_member_id": str(p.cohort_member_id),
            "progress_id": str(p.id),
            "status": p.status,
            "overdue": _is_overdue(
                due_date=milestones_by_id[p.milestone_id].due_date
                if p.milestone_id in milestones_by_id
                else None,
                status=p.status,
                as_of=as_of,
            ),
            "evidence_links": p.evidence_links,
        }
        for p in raw["progress"]
    ]

    board = {"milestones": milestones, "members": members, "cells": cells}
    if milestones or members:  # never cache an empty/missing-cohort shape
        await redis_update_key(key, _CachedBoard(**board), CACHE_TTL_SECONDS)
    return board
