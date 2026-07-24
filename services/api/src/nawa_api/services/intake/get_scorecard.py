"""Cached full-scorecard read (06-intake-copilot.md §6.1).

Key services:intake:get_scorecard:<application_id>, TTL 300s. Invalidated by
scoring, hidden-gem, dedup, decision, and rubric writes — the same set that
touches services:intake:list_shortlist:*.

Presigned document links are NOT yet implemented: no object-storage client
(MinIO/S3 presign helper) exists anywhere in the codebase yet — only
`storage_key` strings are recorded. Documents are returned with their
metadata (file name, kind, mime type); the `url` field is null until that
infrastructure exists.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from nawa_api.contracts.errors import ERR_NOT_FOUND
from nawa_api.db.intake.get_active_rubric_db import get_active_rubric_db
from nawa_api.db.intake.get_application_db import get_application_db
from nawa_api.db.intake.list_application_documents_db import list_application_documents_db
from nawa_api.db.intake.list_decisions_for_application_db import (
    list_decisions_for_application_db,
)
from nawa_api.db.intake.list_scorecard_criteria_db import list_scorecard_criteria_db
from nawa_api.db.intake.list_scorecards_for_application_db import (
    list_scorecards_for_application_db,
)
from nawa_api.db.programs.get_program_cycle_db import get_program_cycle_db
from nawa_api.runtime.redis import redis_retrieve_key, redis_update_key
from nawa_api.services.intake._dto import application_dto
from nawa_api.services.intake.list_dedup_matches import list_dedup_matches

CACHE_TTL_SECONDS = 300
_KEY_PREFIX = "services:intake:get_scorecard"


class _CachedScorecard(BaseModel):
    item: dict


def cache_key(application_id: uuid.UUID) -> str:
    return f"{_KEY_PREFIX}:{application_id}"


def _scorecard_dto(scorecard, criteria: list) -> dict:
    return {
        "id": str(scorecard.id),
        "rubric_id": str(scorecard.rubric_id),
        "rubric_version": scorecard.rubric_version,
        "prompt_version": scorecard.prompt_version,
        "source": scorecard.source,
        "total_score": scorecard.total_score,
        "confidence": scorecard.confidence,
        "rationale_ar": scorecard.rationale_ar,
        "rationale_en": scorecard.rationale_en,
        "hidden_gem": scorecard.hidden_gem,
        "hidden_gem_reason_ar": scorecard.hidden_gem_reason_ar,
        "hidden_gem_reason_en": scorecard.hidden_gem_reason_en,
        "model": scorecard.model,
        "status": scorecard.status,
        "created_at": scorecard.created_at.isoformat(),
        "criteria": [
            {
                "criterion_key": c.criterion_key,
                "score": c.score,
                "weight": c.weight,
                "rationale_ar": c.rationale_ar,
                "rationale_en": c.rationale_en,
                "citations": c.citations,
            }
            for c in criteria
        ],
    }


def _document_dto(doc) -> dict:
    return {
        "id": str(doc.id),
        "file_name": doc.file_name,
        "mime_type": doc.mime_type,
        "kind": doc.kind,
        "size_bytes": doc.size_bytes,
        "url": None,  # presigning not yet implemented anywhere in the codebase
        "created_at": doc.created_at.isoformat(),
    }


def _decision_dto(decision) -> dict:
    return {
        "id": str(decision.id),
        "decided_by": str(decision.decided_by),
        "decision": decision.decision,
        "reason": decision.reason,
        "previous_value": decision.previous_value,
        "new_value": decision.new_value,
        "created_at": decision.created_at.isoformat(),
    }


async def get_scorecard(*, application_id: uuid.UUID) -> dict:
    key = cache_key(application_id)
    cached = await redis_retrieve_key(key, _CachedScorecard)
    if cached is not None:
        return cached.item

    application = await get_application_db(application_id=application_id)
    if application is None:
        raise ERR_NOT_FOUND

    cycle = await get_program_cycle_db(cycle_id=application.cycle_id)
    active_rubric_id = None
    if cycle is not None:
        active_rubric = await get_active_rubric_db(program_id=cycle.program_id)
        active_rubric_id = active_rubric.id if active_rubric is not None else None

    scorecards = await list_scorecards_for_application_db(application_id=application_id)
    ai_scorecards = [sc for sc in scorecards if sc.source == "ai"]
    current = next((sc for sc in ai_scorecards if sc.rubric_id == active_rubric_id), None)
    history = [sc for sc in ai_scorecards if sc is not current]

    current_criteria = (
        await list_scorecard_criteria_db(scorecard_ids=[current.id]) if current else []
    )

    documents = await list_application_documents_db(application_id=application_id)
    dedup_matches = await list_dedup_matches(application_id=application_id)
    decisions = await list_decisions_for_application_db(application_id=application_id)

    item = {
        "application": application_dto(application),
        "scorecard": _scorecard_dto(current, current_criteria) if current else None,
        "scorecard_history": [_scorecard_dto(sc, []) for sc in history],
        "dedup_matches": dedup_matches,
        "documents": [_document_dto(d) for d in documents],
        "decisions": [_decision_dto(d) for d in decisions],
    }
    await redis_update_key(key, _CachedScorecard(item=item), CACHE_TTL_SECONDS)
    return item
