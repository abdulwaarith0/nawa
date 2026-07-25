"""Founder-drivable progress update (07-journey-copilot.md §2.1). Narrower
than the manager review path: status only moves not_started -> in_progress
-> submitted, plus editing evidence_links and the founder's own note.
Founders can never set done/blocked/waived — the schema-encoded
authorization line lives here, service-side (contract input already narrows
the field set; this enforces the transition graph).

Ownership: a progress id that doesn't belong to the caller's founder
profile is ERR_NOT_FOUND (404), never ERR_UNAUTHORIZED (403) — foreign ids
are never confirmed to exist (canon).

Invalidates the exact touched cohort/member keys (recomputed) plus the
cross-domain reports glob (a no-op until 09-reports-kpi-engine.md exists).
"""

from __future__ import annotations

import uuid

from nawa_api.contracts.errors import ERR_INVALID_FIELDS, ERR_NOT_FOUND
from nawa_api.db.journey.get_milestone_db import get_milestone_db
from nawa_api.db.journey.get_milestone_progress_db import get_milestone_progress_db
from nawa_api.db.journey.update_milestone_progress_db import update_milestone_progress_db
from nawa_api.services.journey.get_cohort_board import cache_key as board_cache_key
from nawa_api.services.journey.get_member_timeline import cache_key as timeline_cache_key
from nawa_api.services.journey.list_at_risk import cache_key as at_risk_cache_key
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys
from nawa_api.utils.publish_event import publish_event

_ALLOWED_STATUSES = frozenset({"not_started", "in_progress", "submitted"})
_TRANSITIONS: dict[str, frozenset[str]] = {
    "not_started": frozenset({"in_progress"}),
    "in_progress": frozenset({"submitted"}),
    "submitted": frozenset(),
}


async def update_milestone_progress(
    *,
    progress_id: uuid.UUID,
    founder_profile_id: uuid.UUID,
    updated_by_user_id: uuid.UUID,
    status: str | None = None,
    note_ar: str | None = None,
    note_en: str | None = None,
    evidence_links: list[dict] | None = None,
) -> dict:
    row = await get_milestone_progress_db(progress_id=progress_id)
    if row is None or row.founder_profile_id != founder_profile_id:
        raise ERR_NOT_FOUND

    patch: dict = {}
    if status is not None:
        if status not in _ALLOWED_STATUSES:
            raise ERR_INVALID_FIELDS
        if status != row.status and status not in _TRANSITIONS.get(row.status, frozenset()):
            raise ERR_INVALID_FIELDS
        patch["status"] = status
    if note_ar is not None:
        patch["note_ar"] = note_ar
    if note_en is not None:
        patch["note_en"] = note_en
    if evidence_links is not None:
        patch["evidence_links"] = evidence_links
    if not patch:
        raise ERR_INVALID_FIELDS

    ok = await update_milestone_progress_db(
        progress_id=progress_id, patch=patch, updated_by_user_id=updated_by_user_id
    )
    if not ok:
        raise ERR_INVALID_FIELDS

    milestone = await get_milestone_db(milestone_id=row.milestone_id)
    cohort_id = milestone.cohort_id if milestone is not None else None
    if cohort_id is not None:
        await invalidate_cache_keys(
            board_cache_key(cohort_id=cohort_id),
            timeline_cache_key(founder_profile_id=founder_profile_id, cohort_id=cohort_id),
            at_risk_cache_key(cohort_id=cohort_id),
            "services:reports:get_portfolio:*",
        )
        await publish_event(
            f"events:journey:{cohort_id}",
            {
                "type": "journey.progress.updated",
                "cohort_id": str(cohort_id),
                "milestone_id": str(row.milestone_id),
                "cohort_member_id": str(row.cohort_member_id),
                "status": patch.get("status", row.status),
            },
        )

    updated = await get_milestone_progress_db(progress_id=progress_id)
    return {
        "id": str(updated.id),
        "milestone_id": str(updated.milestone_id),
        "status": updated.status,
        "note_ar": updated.note_ar,
        "note_en": updated.note_en,
        "evidence_links": updated.evidence_links,
    }
