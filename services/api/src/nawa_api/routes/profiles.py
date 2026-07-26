"""Profile self-service routes ("me" semantics — always the caller's own
data, no permission catalog entry needed beyond being signed in)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from nawa_api.contracts.errors import ERR_NOT_FOUND
from nawa_api.contracts.iam import Permission
from nawa_api.db.profiles.get_founder_profile_by_user_id_db import (
    get_founder_profile_by_user_id_db,
)
from nawa_api.middleware.iam import require_permission
from nawa_api.services.profiles.get_founder_profile import get_founder_profile
from nawa_api.services.profiles.list_profile_program_history import (
    list_profile_program_history,
)
from nawa_api.utils.envelope import ok

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me/program-history")
async def get_my_program_history_route():
    session = await require_permission()
    profile = await get_founder_profile_by_user_id_db(user_id=uuid.UUID(session.sub))
    if profile is None:
        raise ERR_NOT_FOUND
    return ok(await list_profile_program_history(profile_id=profile.id))


@router.get("/{handle}")
async def get_profile_by_handle_route(handle: str):
    session = await require_permission(Permission.COMMUNITY_READ)
    profile = await get_founder_profile(handle=handle, viewer_user_id=uuid.UUID(session.sub))
    if profile is None:
        raise ERR_NOT_FOUND
    return ok(profile)
