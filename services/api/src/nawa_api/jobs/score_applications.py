"""Rubric scoring with verified citations (06-intake-copilot.md §3).

Per-application: render the current rubric + the application's own text
through the slice-3 gateway (subject=("application", id), so the payload is
pseudonymized), validate the draft's citations resolve verbatim against the
application's own answers/documents, and — only once a draft checks out —
compute the weighted total in Python (the model never does arithmetic we can
do exactly) and persist scorecards + scorecard_criteria (03's schema, exactly).

A draft that fails validate_scorecard is a hallucination, not a schema error,
so it can't be repaired by the gateway's own JSON-repair loop — this job runs
its own semantic repair loop, re-asking the model up to SCORE_REPAIR_ATTEMPTS
times before giving up. There is no `score_failed` application status (03's
vocabulary doesn't have one): a scoring failure leaves the application
`normalized` and retriable, exactly like a budget stop per §3.3 — never
dropped, never auto-rejected.
"""

from __future__ import annotations

import uuid

from nawa_api.ai import gateway
from nawa_api.ai.prompts import get_template
from nawa_api.ai.prompts.score_application import ScoreApplicationInput, ScorecardDraft
from nawa_api.contracts.errors import ERR_AI_MALFORMED_OUTPUT, ApiError
from nawa_api.db.intake.create_scorecard_criterion_db import create_scorecard_criterion_db
from nawa_api.db.intake.create_scorecard_db import create_scorecard_db
from nawa_api.db.intake.get_application_db import get_application_db
from nawa_api.db.intake.get_rubric_db import get_rubric_db
from nawa_api.db.intake.list_application_documents_db import list_application_documents_db
from nawa_api.db.intake.update_application_scoring_db import update_application_scoring_db
from nawa_api.services.intake.validate_scorecard import validate_scorecard
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys
from nawa_api.utils.logger import get_logger

SCORE_REPAIR_ATTEMPTS = 3  # total tries (incl. the first) before giving up


def _rubric_text(criteria: list[dict]) -> str:
    lines = []
    for c in criteria:
        label = c.get("label_en") or c.get("label_ar") or c["key"]
        guidance = " / ".join(g for g in (c.get("guidance_en"), c.get("guidance_ar")) if g)
        lines.append(
            f"- {c['key']} ({label}), weight {c['weight']}, scale 0-{c['scale_max']}: {guidance}"
        )
    return "\n".join(lines)


def _application_text(application) -> str:
    parts = [f"{key}: {value}" for key, value in application.original_answers.items()]
    if application.summary:
        parts.append(f"summary: {application.summary}")
    return "\n".join(parts)


async def score_application(
    _ctx: dict | None = None,
    application_id: str | uuid.UUID = "",
    rubric_id: str | uuid.UUID = "",
    cycle_id: uuid.UUID | None = None,
) -> str:
    aid = uuid.UUID(str(application_id))
    rid = uuid.UUID(str(rubric_id))

    application = await get_application_db(application_id=aid)
    if application is None:
        return "missing"
    rubric = await get_rubric_db(rubric_id=rid)
    if rubric is None:
        return "missing"

    criterion_keys = {c["key"] for c in rubric.criteria}
    weight_by_key = {c["key"]: c["weight"] for c in rubric.criteria}
    scale_by_key = {c["key"]: c["scale_max"] for c in rubric.criteria}
    documents = await list_application_documents_db(application_id=aid)
    document_texts = {doc.id: doc.extracted_text for doc in documents if doc.extracted_text}

    request = get_template("intake.score").render(
        ScoreApplicationInput(
            rubric=_rubric_text(rubric.criteria),
            application_text=_application_text(application),
        )
    )

    try:
        draft: ScorecardDraft | None = None
        model_name: str | None = None
        for _ in range(SCORE_REPAIR_ATTEMPTS):
            candidate, resp = await gateway.complete_structured(
                request, ScorecardDraft, subject=("application", aid), cycle_id=cycle_id
            )
            try:
                validate_scorecard(
                    candidate,
                    criterion_keys=criterion_keys,
                    original_answers=application.original_answers,
                    document_texts=document_texts,
                )
            except ApiError:
                continue
            draft, model_name = candidate, resp.model
            break
        if draft is None:
            raise ERR_AI_MALFORMED_OUTPUT

        total_score = (
            sum(
                (criterion.score / scale_by_key[criterion.criterion_key])
                * weight_by_key[criterion.criterion_key]
                for criterion in draft.criteria
            )
            * 100
        )

        scorecard = await create_scorecard_db(
            application_id=aid,
            rubric_id=rid,
            rubric_version=rubric.version,
            prompt_version=get_template("intake.score").version,
            source="ai",
            total_score=total_score,
            confidence=draft.confidence,
            rationale_ar=draft.rationale_ar,
            rationale_en=draft.rationale_en,
            model=model_name,
        )
        for criterion in draft.criteria:
            await create_scorecard_criterion_db(
                scorecard_id=scorecard.id,
                criterion_key=criterion.criterion_key,
                score=criterion.score,
                weight=weight_by_key[criterion.criterion_key],
                rationale_ar=criterion.rationale_ar,
                rationale_en=criterion.rationale_en,
                citations=[citation.model_dump() for citation in criterion.citations],
            )
        await update_application_scoring_db(application_id=aid, total_score=total_score)
        status = "scored"
    except ApiError as exc:
        get_logger().warning("score_failed", application_id=str(aid), reason=exc.message)
        status = "score_failed"

    await invalidate_cache_keys(
        f"services:intake:get_application:{aid}",
        "services:intake:list_applications:*",
        "services:intake:list_shortlist:*",
    )
    return status
