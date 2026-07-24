"""Hidden-gem second pass over low scorers (06-intake-copilot.md §5).

The failure mode this exists to prevent: a strong idea written poorly — rural
applicants, non-native writers — dies in a keyword filter or a low
presentation-weighted score. After batch scoring, takes the bottom
HIDDEN_GEM_BAND (40%) of a cycle's scored applications by total_score and
runs the hidden_gem_review prompt — substance over presentation — against
each one's own AI scorecard.

The flag never touches total_score; it's a signal beside the ranking, not a
correction of it (03's ruling — hidden_gem lives on the scorecard row). A
repair-loop exhaustion just leaves the scorecard's existing hidden_gem=False
untouched — never a hard failure state, same philosophy as scoring itself.
"""

from __future__ import annotations

import math
import uuid

from nawa_api.ai import gateway
from nawa_api.ai.prompts import get_template
from nawa_api.ai.prompts.hidden_gem_review import HiddenGemInput, HiddenGemReview
from nawa_api.contracts.errors import ERR_AI_MALFORMED_OUTPUT, ApiError
from nawa_api.db.intake.list_application_documents_db import list_application_documents_db
from nawa_api.db.intake.list_applications_db import list_applications_db
from nawa_api.db.intake.list_scorecards_for_application_db import (
    list_scorecards_for_application_db,
)
from nawa_api.db.intake.update_scorecard_hidden_gem_db import update_scorecard_hidden_gem_db
from nawa_api.models.intake import Application
from nawa_api.services.intake.validate_hidden_gem_review import validate_hidden_gem_review
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys
from nawa_api.utils.logger import get_logger

HIDDEN_GEM_BAND = 0.4
REVIEW_REPAIR_ATTEMPTS = 3
_PAGE_SIZE = 100
_MAX_PAGES = 200


def _application_text(application: Application) -> str:
    parts = [f"{key}: {value}" for key, value in application.original_answers.items()]
    if application.summary:
        parts.append(f"summary: {application.summary}")
    return "\n".join(parts)


async def _list_all_scored_applications(cycle_id: uuid.UUID) -> list[Application]:
    applications: list[Application] = []
    offset = 0
    for _ in range(_MAX_PAGES):
        page = await list_applications_db(
            cycle_id=cycle_id, status="scored", limit=_PAGE_SIZE, offset=offset
        )
        applications.extend(page)
        if len(page) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    return applications


def _bottom_band(applications: list[Application], band: float) -> list[Application]:
    ranked = sorted(applications, key=lambda a: (a.ai_total_score is None, a.ai_total_score))
    cutoff = math.ceil(len(ranked) * band)
    return ranked[:cutoff]


async def _review_one(
    application: Application,
    *,
    cycle_id: uuid.UUID,
    provider_name: str | None = None,
    task_override: str | None = None,
) -> HiddenGemReview | None:
    """`provider_name`/`task_override` exist for the eval harness
    (06-intake-copilot.md §8) reusing this exact per-application review path
    against a golden entry — see score_applications.py's `score_application`
    for the same reasoning."""
    documents = await list_application_documents_db(application_id=application.id)
    document_texts = {doc.id: doc.extracted_text for doc in documents if doc.extracted_text}
    request = get_template("intake.hidden_gem").render(
        HiddenGemInput(application_text=_application_text(application))
    )
    if task_override:
        request = request.model_copy(update={"task": task_override})

    for _ in range(REVIEW_REPAIR_ATTEMPTS):
        candidate, _resp = await gateway.complete_structured(
            request,
            HiddenGemReview,
            subject=("application", application.id),
            cycle_id=cycle_id,
            provider_name=provider_name,
        )
        try:
            validate_hidden_gem_review(
                candidate,
                original_answers=application.original_answers,
                document_texts=document_texts,
            )
        except ApiError:
            continue
        return candidate
    return None


async def hidden_gem_scan(_ctx: dict | None = None, cycle_id: str | uuid.UUID = "") -> dict:
    cid = uuid.UUID(str(cycle_id))
    candidates = _bottom_band(await _list_all_scored_applications(cid), HIDDEN_GEM_BAND)

    flagged = failed = 0
    for application in candidates:
        scorecards = await list_scorecards_for_application_db(application_id=application.id)
        scorecard = next((sc for sc in scorecards if sc.source == "ai"), None)
        if scorecard is None:
            continue

        try:
            review = await _review_one(application, cycle_id=cid)
            if review is None:
                raise ERR_AI_MALFORMED_OUTPUT
            await update_scorecard_hidden_gem_db(
                scorecard_id=scorecard.id,
                hidden_gem=review.is_hidden_gem,
                hidden_gem_reason_ar=review.reason_ar,
                hidden_gem_reason_en=review.reason_en,
            )
            if review.is_hidden_gem:
                flagged += 1
        except ApiError as exc:
            failed += 1
            get_logger().warning(
                "hidden_gem_review_failed", application_id=str(application.id), reason=exc.message
            )

    if candidates:
        await invalidate_cache_keys("services:intake:list_shortlist:*")

    return {"total": len(candidates), "flagged": flagged, "failed": failed}
