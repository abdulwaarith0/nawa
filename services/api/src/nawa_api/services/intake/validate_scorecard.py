"""Post-schema validation for scorecard drafts (06-intake-copilot.md §3.1).

The schema enforces shape; this enforces truth. Pure and side-effect-free —
no DB, no gateway — so it is unit-tested in complete isolation. Two checks,
both mandatory:

1. The draft's criterion keys must exactly match the rubric's — no more, no
   fewer, nothing renamed.
2. Every citation's `source` must resolve to a real place in the application
   and its `quote` must appear verbatim (see `_citations.citations_are_verbatim`
   — shared with hidden-gem review validation, per spec).

A citation that doesn't check out is a hallucination, and a hallucinated
quote means the whole scorecard is untrustworthy — there is no partial
credit. The caller re-asks the model (a repair loop) rather than persist
anything from a draft that fails this check.
"""

from __future__ import annotations

import uuid

from nawa_api.ai.prompts.score_application import ScorecardDraft
from nawa_api.contracts.errors import ERR_AI_MALFORMED_OUTPUT
from nawa_api.services.intake._citations import citations_are_verbatim


def validate_scorecard(
    draft: ScorecardDraft,
    *,
    criterion_keys: set[str],
    original_answers: dict[str, str],
    document_texts: dict[uuid.UUID, str] | None = None,
) -> None:
    """Raises ERR_AI_MALFORMED_OUTPUT if the draft's keys or citations don't
    check out. Returns None (no exception) when the draft is trustworthy."""
    draft_keys = {criterion.criterion_key for criterion in draft.criteria}
    if draft_keys != criterion_keys:
        raise ERR_AI_MALFORMED_OUTPUT

    for criterion in draft.criteria:
        if not citations_are_verbatim(
            criterion.citations, original_answers=original_answers, document_texts=document_texts
        ):
            raise ERR_AI_MALFORMED_OUTPUT
