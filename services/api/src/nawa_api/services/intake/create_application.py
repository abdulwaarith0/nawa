"""Create a single application (06-intake-copilot.md §2.1).

Shared by single-form entry and the bulk-upload arq job. original_answers is
stored verbatim before any model sees it; source_language starts 'en' and the
normalize job (detect_language) overwrites it. Writes invalidate the application
list + shortlist caches.
"""

from __future__ import annotations

import uuid

from nawa_api.contracts.errors import ERR_INVALID_FIELDS
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.services.intake._dto import application_dto
from nawa_api.services.intake.parse_upload import ParsedApplication
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys


async def create_application(
    *,
    cycle_id: uuid.UUID,
    parsed: ParsedApplication,
    source_upload_id: uuid.UUID | None = None,
    source_language: str = "en",
) -> dict:
    # No phone/country columns on applications — preserve them into raw_extra.
    extra = dict(parsed.raw_extra)
    if parsed.phone:
        extra["phone"] = parsed.phone
    if parsed.country:
        extra["country"] = parsed.country

    row = await create_application_db(
        cycle_id=cycle_id,
        applicant_name=parsed.applicant_name,
        applicant_email=parsed.applicant_email,
        source_language=source_language,
        original_answers=parsed.original_answers,
        raw_extra=extra,
        source_upload_id=source_upload_id,
        status="submitted",
    )
    if row is None:
        raise ERR_INVALID_FIELDS
    await invalidate_cache_keys(
        "services:intake:list_applications:*", "services:intake:list_shortlist:*"
    )
    return application_dto(row)
