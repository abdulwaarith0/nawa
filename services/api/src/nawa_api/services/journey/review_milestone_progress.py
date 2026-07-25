"""Manager review path (07-journey-copilot.md §2.1): submitted -> done
(accept evidence), any -> blocked / any -> waived (both require a note),
done -> submitted (reopen). Each review stamps reviewed_by_user_id; the
route layer audit-wraps the call (action journey.progress.review).

Invalidates the exact touched cohort/member keys plus the cross-domain
reports glob, same as the founder path.
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

_ALLOWED_STATUSES = frozenset({"done", "blocked", "waived", "submitted"})
_NOTE_REQUIRED_STATUSES = frozenset({"blocked", "waived"})


def _transition_allowed(*, current: str, new: str) -> bool:
    if new == "blocked" or new == "waived":
        return True
    if new == "done":
        return current == "submitted"
    if new == "submitted":
        return current == "done"
    return False


async def review_milestone_progress(
    *,
    progress_id: uuid.UUID,
    reviewed_by_user_id: uuid.UUID,
    status: str,
    note_ar: str | None = None,
    note_en: str | None = None,
) -> dict:
    if status not in _ALLOWED_STATUSES:
        raise ERR_INVALID_FIELDS

    row = await get_milestone_progress_db(progress_id=progress_id)
    if row is None:
        raise ERR_NOT_FOUND

    if not _transition_allowed(current=row.status, new=status):
        raise ERR_INVALID_FIELDS
    if status in _NOTE_REQUIRED_STATUSES and not note_ar and not note_en:
        raise ERR_INVALID_FIELDS

    patch: dict = {"status": status, "reviewed_by_user_id": reviewed_by_user_id}
    if note_ar is not None:
        patch["note_ar"] = note_ar
    if note_en is not None:
        patch["note_en"] = note_en

    ok = await update_milestone_progress_db(
        progress_id=progress_id, patch=patch, updated_by_user_id=reviewed_by_user_id
    )
    if not ok:
        raise ERR_INVALID_FIELDS

    milestone = await get_milestone_db(milestone_id=row.milestone_id)
    cohort_id = milestone.cohort_id if milestone is not None else None
    if cohort_id is not None:
        await invalidate_cache_keys(
            board_cache_key(cohort_id=cohort_id),
            timeline_cache_key(
                founder_profile_id=row.founder_profile_id, cohort_id=cohort_id
            ),
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
                "status": status,
            },
        )

    updated = await get_milestone_progress_db(progress_id=progress_id)
    return {
        "id": str(updated.id),
        "milestone_id": str(updated.milestone_id),
        "status": updated.status,
        "note_ar": updated.note_ar,
        "note_en": updated.note_en,
        "reviewed_by_user_id": str(updated.reviewed_by_user_id)
        if updated.reviewed_by_user_id
        else None,
    }
