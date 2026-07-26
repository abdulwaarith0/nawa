"""Community routes (08-community-hub.md). This slice cut builds only
Deliverable B's directory read — the requests desk, opportunities board,
mentor matching, and moderation queue are explicitly out of scope here."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from nawa_api.contracts.iam import Permission
from nawa_api.middleware.iam import require_permission
from nawa_api.services.community.list_directory import list_directory
from nawa_api.utils.envelope import ok

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/directory")
async def list_directory_route(
    q: str | None = None,
    domains: list[str] | None = Query(default=None),
    skills: list[str] | None = Query(default=None),
    sector: str | None = None,
    country: str | None = None,
    program_id: uuid.UUID | None = None,
    stage: str | None = None,
    mentors: bool | None = None,
    limit: int | None = None,
    offset: int | None = None,
):
    await require_permission(Permission.COMMUNITY_READ)
    return ok(
        await list_directory(
            q=q,
            domains=domains,
            skills=skills,
            sector=sector,
            country=country,
            program_id=program_id,
            stage=stage,
            mentors=mentors,
            limit=limit,
            offset=offset,
        )
    )
