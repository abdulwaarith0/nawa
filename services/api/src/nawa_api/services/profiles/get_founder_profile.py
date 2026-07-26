"""Public founder-profile page read (08-community-hub.md §2.1): identity,
venture, the denormalized KPI snapshot, derived program history, skills/
domains, and active asks.

Visibility (never a 403 — a hidden/foreign handle looks identical to a
missing one): `is_public=True` on a profile whose owning user is active ->
any caller with `nawa:community:read`. `is_public=False` -> only the owner
(session user_id == the profile's user_id) or a caller holding
`nawa:profiles:read` ("view profiles beyond the public projection" — the
staff-ish permission per the catalog) may see it; everyone else gets `None`
back and the route turns that into 404.

No caching here (out of scope for this slice's cut) — this composes
`list_profile_program_history`, which is already cached on its own key.
"""

from __future__ import annotations

import uuid

from nawa_api.contracts.iam import Permission
from nawa_api.db.profiles.get_profile_by_handle_any_status_db import (
    get_profile_by_handle_any_status_db,
)
from nawa_api.db.users.get_user_by_id_db import get_user_by_id_db
from nawa_api.services.iam.resolve_effective_permissions import resolve_effective_permissions
from nawa_api.services.profiles.list_profile_program_history import (
    list_profile_program_history,
)


def _dto(profile) -> dict:
    return {
        "handle": profile.handle,
        "display_name_ar": profile.display_name_ar,
        "display_name_en": profile.display_name_en,
        "headline_ar": profile.headline_ar,
        "headline_en": profile.headline_en,
        "bio_ar": profile.bio_ar,
        "bio_en": profile.bio_en,
        "venture_name_ar": profile.venture_name_ar,
        "venture_name_en": profile.venture_name_en,
        "venture_summary_ar": profile.venture_summary_ar,
        "venture_summary_en": profile.venture_summary_en,
        "stage": profile.stage,
        "sector": profile.sector,
        "country": profile.country,
        "city": profile.city,
        "website": profile.website,
        "links": profile.links,
        "skills": profile.skills,
        "domains": profile.domains,
        "is_mentor_eligible": profile.is_mentor_eligible,
        "kpi_snapshot": profile.kpi_snapshot,
        "kpi_snapshot_at": (
            profile.kpi_snapshot_at.isoformat() if profile.kpi_snapshot_at else None
        ),
        "asks": [ask for ask in (profile.asks or []) if ask.get("active")],
    }


async def get_founder_profile(*, handle: str, viewer_user_id: uuid.UUID) -> dict | None:
    profile = await get_profile_by_handle_any_status_db(handle=handle)
    if profile is None:
        return None

    is_owner = profile.user_id == viewer_user_id
    if not is_owner:
        owner = await get_user_by_id_db(user_id=profile.user_id)
        if owner is None or not owner.is_active:
            return None
        if not profile.is_public:
            effective = await resolve_effective_permissions(user_id=viewer_user_id)
            if Permission.PROFILES_READ not in effective:
                return None

    data = _dto(profile)
    data["program_history"] = await list_profile_program_history(profile_id=profile.id)
    return data
