"""Human resolution of a dedup flag (06-intake-copilot.md §4).

A match is only ever a flag for human review; resolving it never touches
either application's own status — that stays a separate `decisions` row.
"""

from __future__ import annotations

import uuid

from nawa_api.contracts.errors import ERR_INVALID_FIELDS, ERR_NOT_FOUND
from nawa_api.db.intake.update_dedup_match_status_db import update_dedup_match_status_db
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys

_VALID_STATUSES = frozenset({"confirmed", "dismissed"})


async def resolve_dedup_match(*, match_id: uuid.UUID, status: str, reviewed_by: uuid.UUID) -> dict:
    if status not in _VALID_STATUSES:
        raise ERR_INVALID_FIELDS

    updated = await update_dedup_match_status_db(
        match_id=match_id, status=status, reviewed_by=reviewed_by
    )
    if not updated:
        raise ERR_NOT_FOUND

    await invalidate_cache_keys("services:intake:list_dedup_matches:*")
    return {"id": str(match_id), "status": status, "reviewed_by": str(reviewed_by)}
