"""Language detection + LLM normalization (06-intake-copilot.md §2.2).

Per-application: detect the source language and produce a structured EN
projection, both through the slice-3 gateway with subject=("application", id) so
every payload passes through the pseudonymizer. original_answers is sacred — the
verbatim submission is never modified. An AI failure sends the application to
normalize_failed (visible for staff triage), never dropped, never auto-rejected.
"""

from __future__ import annotations

import uuid

from nawa_api.ai import gateway
from nawa_api.ai.prompts import get_template
from nawa_api.ai.prompts.detect_language import DetectLanguageInput, DetectLanguageOutput
from nawa_api.ai.prompts.normalize_application import (
    NormalizeApplicationInput,
    NormalizeApplicationOutput,
)
from nawa_api.contracts.errors import ApiError
from nawa_api.db.intake.get_application_db import get_application_db
from nawa_api.db.intake.mark_application_normalize_failed_db import (
    mark_application_normalize_failed_db,
)
from nawa_api.db.intake.update_application_normalization_db import (
    update_application_normalization_db,
)
from nawa_api.runtime.redis import get_redis
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys
from nawa_api.utils.logger import get_logger
from nawa_api.utils.publish_event import publish_event


async def _publish_progress(upload_id: uuid.UUID | None, status: str) -> None:
    if upload_id is None:
        return
    field = "done" if status == "normalized" else "failed"
    await get_redis().hincrby(f"jobs:intake:upload:{upload_id}:progress", field, 1)
    await publish_event(f"events:intake:upload:{upload_id}", {"type": "progress", "status": status})


async def normalize_application(
    _ctx: dict | None = None,
    application_id: str | uuid.UUID = "",
    upload_id: str | uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
) -> str:
    aid = uuid.UUID(str(application_id))
    application = await get_application_db(application_id=aid)
    if application is None:
        return "missing"

    raw_text = "\n".join(f"{k}: {v}" for k, v in application.original_answers.items())
    subject = ("application", aid)

    try:
        detect_request = get_template("intake.detect_language").render(
            DetectLanguageInput(text=raw_text)
        )
        detected, _ = await gateway.complete_structured(
            detect_request, DetectLanguageOutput, subject=subject, cycle_id=cycle_id
        )
        language = detected.language  # schema-constrained to ar|en|fr

        normalize_request = get_template("intake.normalize").render(
            NormalizeApplicationInput(raw_text=raw_text, language=language)
        )
        projection, _ = await gateway.complete_structured(
            normalize_request, NormalizeApplicationOutput, subject=subject, cycle_id=cycle_id
        )
        await update_application_normalization_db(
            application_id=aid,
            source_language=language,
            normalized=projection.model_dump(),
            title=projection.title or None,
            summary=projection.summary or None,
        )
        status = "normalized"
    except ApiError as exc:
        await mark_application_normalize_failed_db(application_id=aid, reason=exc.message)
        get_logger().warning("normalize_failed", application_id=str(aid), reason=exc.message)
        status = "normalize_failed"

    await invalidate_cache_keys(
        f"services:intake:get_application:{aid}",
        "services:intake:list_applications:*",
        "services:intake:list_shortlist:*",
    )
    await _publish_progress(uuid.UUID(str(upload_id)) if upload_id else None, status)
    return status
