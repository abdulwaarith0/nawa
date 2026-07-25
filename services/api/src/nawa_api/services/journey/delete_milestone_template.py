"""Delete a milestone template (07-journey-copilot.md §2.1/§2.3). Refuses to
touch an id that isn't a template row — 404, never a cohort milestone.

Invalidates services:journey:list_milestone_templates:*.
"""

from __future__ import annotations

import uuid

from nawa_api.contracts.errors import ERR_NOT_FOUND
from nawa_api.db.journey.delete_milestone_db import delete_milestone_db
from nawa_api.db.journey.get_milestone_db import get_milestone_db
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys


async def delete_milestone_template(*, milestone_id: uuid.UUID) -> None:
    row = await get_milestone_db(milestone_id=milestone_id)
    if row is None or row.scope != "template":
        raise ERR_NOT_FOUND
    ok = await delete_milestone_db(milestone_id=milestone_id)
    if not ok:
        raise ERR_NOT_FOUND
    await invalidate_cache_keys("services:journey:list_milestone_templates:*")
