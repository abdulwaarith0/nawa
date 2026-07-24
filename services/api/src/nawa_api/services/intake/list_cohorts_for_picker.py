"""Cohort picker for the Accept-decision panel (06-intake-copilot.md §6.2 —
"Accept-into-cohort with a cohort picker scoped to the cycle"). Not cached:
same reasoning as list_cycles_for_picker.py — low-traffic, low-volatility
config-shaped data.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from nawa_api.db.cohorts.list_cohorts_db import list_cohorts_db


class CohortPickerItem(BaseModel):
    id: uuid.UUID
    name_ar: str | None
    name_en: str | None
    starts_at: str
    ends_at: str | None


async def list_cohorts_for_picker(*, cycle_id: uuid.UUID) -> list[dict]:
    cohorts = await list_cohorts_db(cycle_id=cycle_id, limit=100)
    return [
        CohortPickerItem(
            id=cohort.id,
            name_ar=cohort.name_ar,
            name_en=cohort.name_en,
            starts_at=cohort.starts_at.isoformat(),
            ends_at=cohort.ends_at.isoformat() if cohort.ends_at else None,
        ).model_dump(mode="json")
        for cohort in cohorts
    ]
