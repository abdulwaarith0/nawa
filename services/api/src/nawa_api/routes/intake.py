"""Intake console routes (06-intake-copilot.md §6.1, §6.2).

Export (§6.1's XLSX bullet) and rubric-management routes are deferred to
their own chunks, same as the batch-score and dedup-match routes chunks 5/6
deferred — nothing in the repo enqueues a real arq job from an HTTP route
yet, and that plumbing lands together with the export route.
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from nawa_api.contracts.errors import ApiError
from nawa_api.contracts.iam import Permission
from nawa_api.middleware.iam import require_permission
from nawa_api.services.audit.create_audit_log import create_audit_log
from nawa_api.services.intake.decide_application import decide_application
from nawa_api.services.intake.get_scorecard import get_scorecard
from nawa_api.services.intake.list_shortlist import list_shortlist
from nawa_api.utils.envelope import ok
from nawa_api.utils.request_context import request_id_var

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


class CreateDecisionInput(BaseModel):
    decision: str
    reason: str | None = None
    cohort_id: uuid.UUID | None = None


@router.post("/intake/applications/{id}/decision")
async def create_decision_route(id: uuid.UUID, body: CreateDecisionInput):
    session = await require_permission(Permission.INTAKE_OVERRIDE)
    actor_id = uuid.UUID(session.sub)
    start = time.perf_counter()
    status_code = 500
    result: dict | None = None
    try:
        result = await decide_application(
            application_id=id,
            decision=body.decision,
            reason=body.reason,
            cohort_id=body.cohort_id,
            decided_by=actor_id,
        )
        status_code = 200
        return ok(result)
    except ApiError as exc:
        status_code = exc.code
        raise
    finally:
        # `overridden` is only known once the AI band is computed; a failure
        # before that point (missing application, bad decision value) can't
        # distinguish an attempted override, so it falls back to the plain
        # create action rather than guessing.
        action = "intake.decision.create"
        if result is not None and result.get("overridden"):
            action = "intake.decision.override"
        duration_ms = int((time.perf_counter() - start) * 1000)
        await create_audit_log(
            actor_id=actor_id,
            action=action,
            target_type="intake_application",
            target_id=id,
            status_code=status_code,
            duration_ms=duration_ms,
            request_id=request_id_var.get(),
            body=body.model_dump(),
        )
        if result is not None and result.get("decision") == "accept":
            await create_audit_log(
                actor_id=actor_id,
                action="intake.decision.accept",
                target_type="intake_application",
                target_id=id,
                status_code=status_code,
                duration_ms=duration_ms,
                request_id=request_id_var.get(),
                body=body.model_dump(),
            )
