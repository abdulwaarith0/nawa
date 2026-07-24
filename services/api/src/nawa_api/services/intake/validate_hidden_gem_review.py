"""Post-schema validation for hidden-gem reviews (06-intake-copilot.md §5) —
"the same verbatim-citation validation as scoring", per spec. Unlike scoring
there is no rubric/criterion-key check here; a hidden-gem review only has one
flat citations list to verify.
"""

from __future__ import annotations

import uuid

from nawa_api.ai.prompts.hidden_gem_review import HiddenGemReview
from nawa_api.contracts.errors import ERR_AI_MALFORMED_OUTPUT
from nawa_api.services.intake._citations import citations_are_verbatim


def validate_hidden_gem_review(
    review: HiddenGemReview,
    *,
    original_answers: dict[str, str],
    document_texts: dict[uuid.UUID, str] | None = None,
) -> None:
    """Raises ERR_AI_MALFORMED_OUTPUT if any citation doesn't resolve to a real,
    verbatim quote in the application."""
    if not citations_are_verbatim(
        review.citations, original_answers=original_answers, document_texts=document_texts
    ):
        raise ERR_AI_MALFORMED_OUTPUT
