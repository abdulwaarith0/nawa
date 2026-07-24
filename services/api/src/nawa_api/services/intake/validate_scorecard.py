"""Post-schema validation for scorecard drafts (06-intake-copilot.md §3.1).

The schema enforces shape; this enforces truth. Pure and side-effect-free —
no DB, no gateway — so it is unit-tested in complete isolation. Two checks,
both mandatory:

1. The draft's criterion keys must exactly match the rubric's — no more, no
   fewer, nothing renamed.
2. Every citation's `source` must resolve to a real place in the application
   (an `answer:<question_key>` in `original_answers`, or a
   `document:<document_id>` with extracted text), and its `quote` must appear
   verbatim (after whitespace normalization) in that source's text.

A citation that doesn't check out is a hallucination, and a hallucinated
quote means the whole scorecard is untrustworthy — there is no partial
credit. The caller re-asks the model (a repair loop) rather than persist
anything from a draft that fails this check.
"""

from __future__ import annotations

import re
import uuid

from nawa_api.ai.prompts.score_application import ScorecardDraft
from nawa_api.contracts.errors import ERR_AI_MALFORMED_OUTPUT

_WS_RE = re.compile(r"\s+")


def _normalize_ws(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _resolve_source(
    source: str,
    *,
    original_answers: dict[str, str],
    document_texts: dict[uuid.UUID, str],
) -> str | None:
    if source.startswith("answer:"):
        return original_answers.get(source.removeprefix("answer:"))
    if source.startswith("document:"):
        try:
            doc_id = uuid.UUID(source.removeprefix("document:"))
        except ValueError:
            return None
        return document_texts.get(doc_id)
    return None


def validate_scorecard(
    draft: ScorecardDraft,
    *,
    criterion_keys: set[str],
    original_answers: dict[str, str],
    document_texts: dict[uuid.UUID, str] | None = None,
) -> None:
    """Raises ERR_AI_MALFORMED_OUTPUT if the draft's keys or citations don't
    check out. Returns None (no exception) when the draft is trustworthy."""
    document_texts = document_texts or {}

    draft_keys = {criterion.criterion_key for criterion in draft.criteria}
    if draft_keys != criterion_keys:
        raise ERR_AI_MALFORMED_OUTPUT

    for criterion in draft.criteria:
        for citation in criterion.citations:
            source_text = _resolve_source(
                citation.source, original_answers=original_answers, document_texts=document_texts
            )
            if source_text is None:
                raise ERR_AI_MALFORMED_OUTPUT
            if _normalize_ws(citation.quote) not in _normalize_ws(source_text):
                raise ERR_AI_MALFORMED_OUTPUT
