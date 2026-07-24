"""Semantic dedup + prior-art scan (06-intake-copilot.md §4).

For a freshly embedded application, finds nearest neighbors ACROSS ALL
seasons/cycles (`list_similar_applications_db` is deliberately unscoped by
cycle — the point is that a Season-16 resubmission must surface) above the
site_config-configured similarity floor, unioned with exact `applicant_email`
matches (03's candidate-generation rule). Every hit upserts a dedup_matches
row — idempotent, so re-running the scan converges rather than piling up
duplicate rows or erroring on the unique pair.

A match is only ever a flag for human review — it never touches the
application's own status. Humans resolve it to confirmed/dismissed via the
dedup-match PATCH route, which is deferred to the API-layer chunk along with
the rest of intake's routes (chunk 5 deferred the score route the same way).
"""

from __future__ import annotations

import uuid

from nawa_api.db.intake.get_application_db import get_application_db
from nawa_api.db.intake.list_applications_by_email_db import list_applications_by_email_db
from nawa_api.db.intake.list_similar_applications_db import list_similar_applications_db
from nawa_api.db.intake.upsert_dedup_match_db import upsert_dedup_match_db
from nawa_api.services.site_config.get_site_config import get_site_config
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys

_KNN_CANDIDATES = 10
# If site_config is ever missing the key, fail CLOSED (match nothing) rather
# than guess at a plausible business threshold — there is no hard-coded
# dedup threshold constant in this slice, per spec.
_UNCONFIGURED_THRESHOLD = 1.0
_EXACT_EMAIL_SIMILARITY = 1.0  # no vector score for an exact-email hit


async def _dedup_threshold() -> float:
    values = await get_site_config()
    return float(values.get("intake:dedup_threshold", _UNCONFIGURED_THRESHOLD))


async def dedup_scan(_ctx: dict | None = None, application_id: str | uuid.UUID = "") -> int:
    aid = uuid.UUID(str(application_id))
    application = await get_application_db(application_id=aid)
    if application is None:
        return 0

    threshold = await _dedup_threshold()
    neighbors = await list_similar_applications_db(application_id=aid, k=_KNN_CANDIDATES)
    similarity_by_id = {
        matched_id: similarity for matched_id, similarity in neighbors if similarity >= threshold
    }

    email_matches = await list_applications_by_email_db(
        applicant_email=application.applicant_email
    )
    for row in email_matches:
        if row.id != aid:
            similarity_by_id.setdefault(row.id, _EXACT_EMAIL_SIMILARITY)

    for matched_id, similarity in similarity_by_id.items():
        await upsert_dedup_match_db(
            application_id=aid, matched_application_id=matched_id, similarity=similarity
        )

    if similarity_by_id:
        await invalidate_cache_keys("services:intake:list_dedup_matches:*")
    return len(similarity_by_id)
