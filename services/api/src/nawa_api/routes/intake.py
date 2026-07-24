"""Intake console routes (06-intake-copilot.md §6.1) — read-only for now.

Decisions (§6.2), export (§6.1's XLSX bullet), and rubric-management routes
are deferred to their own chunks, same as the batch-score and dedup-match
routes chunks 5/6 deferred — nothing in the repo enqueues a real arq job
from an HTTP route yet, and that plumbing lands together with those routes.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from nawa_api.contracts.iam import Permission
from nawa_api.middleware.iam import require_permission
from nawa_api.services.intake.get_scorecard import get_scorecard
from nawa_api.services.intake.list_shortlist import list_shortlist
from nawa_api.utils.envelope import ok

router = APIRouter(tags=["intake"])


@router.get("/intake/cycles/{cycle_id}/shortlist")
async def list_shortlist_route(
    cycle_id: uuid.UUID,
    score_band: str | None = None,
    criterion: str | None = None,
    criterion_min: float | None = None,
    flags: str | None = None,  # comma-separated: hidden_gem,dedup_pending,normalize_failed
    language: str | None = None,
    country: str | None = None,
    decision: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    await require_permission(Permission.INTAKE_REVIEW)
    flag_set = frozenset(f.strip() for f in flags.split(",") if f.strip()) if flags else frozenset()
    return ok(
        await list_shortlist(
            cycle_id=cycle_id,
            score_band=score_band,
            criterion=criterion,
            criterion_min=criterion_min,
            flags=flag_set,
            language=language,
            country=country,
            decision=decision,
            q=q,
            limit=min(max(limit, 1), 100),
            offset=max(offset, 0),
        )
    )


@router.get("/intake/applications/{id}/scorecard")
async def get_scorecard_route(id: uuid.UUID):
    await require_permission(Permission.INTAKE_REVIEW)
    return ok(await get_scorecard(application_id=id))
