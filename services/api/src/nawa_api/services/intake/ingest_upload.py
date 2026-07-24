"""Bulk upload ingestion orchestration (06-intake-copilot.md §2.1, §2.2, §4).

Split in two so the route can respond with the 202 envelope (`upload_id` +
row count) before the slow part runs: `create_upload_and_applications`
parses the file, stores it, and writes the provenance + application rows;
`fan_out_processing` then walks normalize -> embed -> dedup per application.
No arq pool is wired into the route layer anywhere in this codebase yet
(`jobs/score_cycle.py` fans out the same way, by awaiting job functions
directly rather than re-enqueueing them), so the route schedules
`fan_out_processing` as a FastAPI background task instead — same
fire-and-forget shape, no new infra.
"""

from __future__ import annotations

import uuid

from nawa_api.contracts.errors import ERR_NOT_FOUND
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_application_upload_db import create_application_upload_db
from nawa_api.db.programs.get_program_cycle_db import get_program_cycle_db
from nawa_api.jobs.dedup_scan import dedup_scan
from nawa_api.jobs.embed_application import embed_application
from nawa_api.jobs.normalize_applications import normalize_application
from nawa_api.runtime.redis import get_redis
from nawa_api.runtime.storage import get_storage_provider
from nawa_api.services.intake.parse_upload import parse_upload
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys

PROGRESS_TTL_SECONDS = 24 * 3600
# Every applications row needs a source_language satisfying the ('ar','en','fr')
# CHECK before normalize_application ever runs and detects the real one.
_PENDING_LANGUAGE = "en"


def progress_key(upload_id: uuid.UUID) -> str:
    return f"jobs:intake:upload:{upload_id}:progress"


def progress_channel(upload_id: uuid.UUID) -> str:
    return f"events:intake:upload:{upload_id}"


async def create_upload_and_applications(
    *,
    cycle_id: uuid.UUID,
    filename: str,
    content: bytes,
    mime_type: str,
    column_map: dict[str, str],
    uploaded_by_user_id: uuid.UUID,
) -> dict:
    cycle = await get_program_cycle_db(cycle_id=cycle_id)
    if cycle is None:
        raise ERR_NOT_FOUND

    parsed = parse_upload(content, filename, column_map)  # raises ERR_INVALID_FIELDS

    upload_id = uuid.uuid4()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    storage_key = f"intake/uploads/{cycle_id}/{upload_id}/source.{ext}"
    await get_storage_provider().put_object(storage_key, content, content_type=mime_type)

    upload_row = await create_application_upload_db(
        id=upload_id,
        cycle_id=cycle_id,
        storage_key=storage_key,
        file_name=filename,
        mime_type=mime_type,
        size_bytes=len(content),
        uploaded_by_user_id=uploaded_by_user_id,
        row_count=len(parsed),
    )
    if upload_row is None:
        raise ERR_NOT_FOUND

    application_ids: list[uuid.UUID] = []
    for row in parsed:
        application = await create_application_db(
            cycle_id=cycle_id,
            applicant_name=row.applicant_name,
            applicant_email=row.applicant_email,
            source_language=_PENDING_LANGUAGE,
            original_answers=row.original_answers,
            raw_extra=row.raw_extra,
            source_upload_id=upload_row.id,
        )
        if application is not None:
            application_ids.append(application.id)

    redis = get_redis()
    key = progress_key(upload_row.id)
    await redis.delete(key)
    await redis.hset(key, mapping={"total": len(application_ids), "done": 0, "failed": 0})
    await redis.expire(key, PROGRESS_TTL_SECONDS)

    await invalidate_cache_keys("services:intake:list_applications:*")

    return {
        "upload_id": upload_row.id,
        "row_count": len(application_ids),
        "application_ids": application_ids,
    }


async def fan_out_processing(
    *, application_ids: list[uuid.UUID], upload_id: uuid.UUID, cycle_id: uuid.UUID
) -> None:
    for application_id in application_ids:
        status = await normalize_application(
            application_id=application_id, upload_id=upload_id, cycle_id=cycle_id
        )
        if status != "normalized":
            continue
        embed_status = await embed_application(application_id=application_id)
        if embed_status == "embedded":
            await dedup_scan(application_id=application_id)
