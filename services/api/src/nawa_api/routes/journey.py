"""Journey console routes — milestone tracking (07-journey-copilot.md
§2.4). Assistant + digest routes ship in later chunks of this slice.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel

from nawa_api.contracts.errors import ERR_NOT_FOUND
from nawa_api.contracts.iam import Permission
from nawa_api.db.cohorts.get_cohort_db import get_cohort_db
from nawa_api.db.cohorts.list_cohort_members_db import list_cohort_members_db
from nawa_api.db.profiles.get_founder_profile_by_user_id_db import (
    get_founder_profile_by_user_id_db,
)
from nawa_api.middleware.audit import audited
from nawa_api.middleware.iam import require_permission
from nawa_api.services.journey.create_milestone_template import create_milestone_template
from nawa_api.services.journey.delete_milestone_template import delete_milestone_template
from nawa_api.services.journey.get_cohort_board import get_cohort_board
from nawa_api.services.journey.get_member_timeline import get_member_timeline
from nawa_api.services.journey.instantiate_cohort_milestones import (
    instantiate_cohort_milestones,
)
from nawa_api.services.journey.list_at_risk import list_at_risk
from nawa_api.services.journey.list_cohort_milestones import list_cohort_milestones
from nawa_api.services.journey.list_milestone_templates import list_milestone_templates
from nawa_api.services.journey.review_milestone_progress import review_milestone_progress
from nawa_api.services.journey.update_cohort_milestone import update_cohort_milestone
from nawa_api.services.journey.update_milestone_progress import update_milestone_progress
from nawa_api.services.journey.update_milestone_template import update_milestone_template
from nawa_api.utils.envelope import created, ok
from nawa_api.utils.request_context import get_session_user
from nawa_api.utils.sse import sse_response

router = APIRouter(prefix="/journey", tags=["journey"])


class CreateMilestoneTemplateInput(BaseModel):
    program_cycle_id: uuid.UUID | None = None
    sequence: int
    title_ar: str | None = None
    title_en: str | None = None
    description_ar: str | None = None
    description_en: str | None = None
    due_offset_days: int | None = None
    evidence_required: bool = False
    config: dict = {}


class UpdateMilestoneTemplateInput(BaseModel):
    title_ar: str | None = None
    title_en: str | None = None
    description_ar: str | None = None
    description_en: str | None = None
    sequence: int | None = None
    due_offset_days: int | None = None
    evidence_required: bool | None = None
    config: dict | None = None


class UpdateCohortMilestoneInput(BaseModel):
    title_ar: str | None = None
    title_en: str | None = None
    description_ar: str | None = None
    description_en: str | None = None
    due_date: date | None = None
    evidence_required: bool | None = None


class UpdateMilestoneProgressInput(BaseModel):
    """Founder-drivable — narrower than the review schema: no `done`,
    `blocked`, `waived`, and no `reviewed_by_user_id` field at all. The
    service enforces the not_started -> in_progress -> submitted graph."""

    status: str | None = None
    note_ar: str | None = None
    note_en: str | None = None
    evidence_links: list[dict] | None = None


class ReviewMilestoneProgressInput(BaseModel):
    status: str
    note_ar: str | None = None
    note_en: str | None = None


async def _own_founder_profile_id() -> uuid.UUID:
    session = get_session_user()
    profile = await get_founder_profile_by_user_id_db(user_id=uuid.UUID(session.sub))
    if profile is None:
        raise ERR_NOT_FOUND
    return profile.id


@router.get("/programs/{program_id}/milestone-templates")
async def list_milestone_templates_route(
    program_id: uuid.UUID, program_cycle_id: uuid.UUID | None = None
):
    await require_permission(Permission.JOURNEY_MANAGE)
    return ok(
        await list_milestone_templates(program_id=program_id, program_cycle_id=program_cycle_id)
    )


@router.post("/programs/{program_id}/milestone-templates", status_code=201)
@audited(action="journey.template.create", target_type="milestone_template")
async def create_milestone_template_route(
    program_id: uuid.UUID, body: CreateMilestoneTemplateInput
):
    await require_permission(Permission.JOURNEY_MANAGE)
    row = await create_milestone_template(program_id=program_id, **body.model_dump())
    return created(row)


@router.patch("/milestone-templates/{id}")
@audited(action="journey.template.update", target_type="milestone_template")
async def update_milestone_template_route(id: uuid.UUID, body: UpdateMilestoneTemplateInput):
    await require_permission(Permission.JOURNEY_MANAGE)
    patch = body.model_dump(exclude_unset=True)
    return ok(await update_milestone_template(milestone_id=id, patch=patch))


@router.delete("/milestone-templates/{id}")
@audited(action="journey.template.delete", target_type="milestone_template")
async def delete_milestone_template_route(id: uuid.UUID):
    await require_permission(Permission.JOURNEY_MANAGE)
    await delete_milestone_template(milestone_id=id)
    return ok(None)


@router.post("/cohorts/{cohort_id}/milestones/instantiate")
@audited(action="journey.milestones.instantiate", target_type="cohort")
async def instantiate_cohort_milestones_route(cohort_id: uuid.UUID):
    await require_permission(Permission.JOURNEY_MANAGE)
    return ok(await instantiate_cohort_milestones(cohort_id=cohort_id))


@router.get("/cohorts/{cohort_id}/milestones")
async def list_cohort_milestones_route(cohort_id: uuid.UUID):
    await require_permission(Permission.JOURNEY_READ)
    return ok(await list_cohort_milestones(cohort_id=cohort_id))


@router.patch("/milestones/{id}")
@audited(action="journey.milestone.update", target_type="milestone")
async def update_cohort_milestone_route(id: uuid.UUID, body: UpdateCohortMilestoneInput):
    await require_permission(Permission.JOURNEY_MANAGE)
    patch = body.model_dump(exclude_unset=True)
    return ok(await update_cohort_milestone(milestone_id=id, patch=patch))


@router.get("/cohorts/{cohort_id}/board")
async def get_cohort_board_route(cohort_id: uuid.UUID):
    await require_permission(Permission.JOURNEY_READ)
    return ok(await get_cohort_board(cohort_id=cohort_id))


@router.get("/cohorts/{cohort_id}/at-risk")
async def list_at_risk_route(cohort_id: uuid.UUID):
    await require_permission(Permission.JOURNEY_READ)
    return ok(await list_at_risk(cohort_id=cohort_id))


@router.get("/me/timeline")
async def get_my_timeline_route(cohort_id: uuid.UUID):
    await require_permission(Permission.JOURNEY_READ)
    profile_id = await _own_founder_profile_id()
    return ok(await get_member_timeline(founder_profile_id=profile_id, cohort_id=cohort_id))


@router.patch("/progress/{id}")
@audited(action="journey.progress.update", target_type="milestone_progress")
async def update_milestone_progress_route(id: uuid.UUID, body: UpdateMilestoneProgressInput):
    session = await require_permission(Permission.JOURNEY_PROGRESS)
    profile_id = await _own_founder_profile_id()
    result = await update_milestone_progress(
        progress_id=id,
        founder_profile_id=profile_id,
        updated_by_user_id=uuid.UUID(session.sub),
        **body.model_dump(exclude_unset=True),
    )
    return ok(result)


@router.patch("/progress/{id}/review")
@audited(action="journey.progress.review", target_type="milestone_progress")
async def review_milestone_progress_route(id: uuid.UUID, body: ReviewMilestoneProgressInput):
    session = await require_permission(Permission.JOURNEY_MANAGE)
    result = await review_milestone_progress(
        progress_id=id,
        reviewed_by_user_id=uuid.UUID(session.sub),
        status=body.status,
        note_ar=body.note_ar,
        note_en=body.note_en,
    )
    return ok(result)


async def _may_view_cohort(*, cohort_id: uuid.UUID, session) -> bool:
    from nawa_api.services.iam.resolve_effective_permissions import (
        resolve_effective_permissions,
    )

    effective = await resolve_effective_permissions(user_id=session.sub)
    if Permission.JOURNEY_MANAGE in effective:
        return True
    profile = await get_founder_profile_by_user_id_db(user_id=uuid.UUID(session.sub))
    if profile is None:
        return False
    members = await list_cohort_members_db(cohort_id=cohort_id, limit=100)
    return any(m.profile_id == profile.id and m.status == "active" for m in members)


@router.get("/cohorts/{cohort_id}/events")
async def cohort_events_route(cohort_id: uuid.UUID):
    session = await require_permission(Permission.JOURNEY_READ)
    cohort = await get_cohort_db(cohort_id=cohort_id)
    if cohort is None:
        raise ERR_NOT_FOUND
    if not await _may_view_cohort(cohort_id=cohort_id, session=session):
        raise ERR_NOT_FOUND
    return sse_response(f"events:journey:{cohort_id}")
