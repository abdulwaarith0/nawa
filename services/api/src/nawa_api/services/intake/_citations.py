"""Shared verbatim-citation check (06-intake-copilot.md §3.1, §5) — used by
both scorecard validation and hidden-gem review validation, since the spec
gives hidden-gem review "the same verbatim-citation validation as scoring".

A citation's `source` must resolve to a real place in the application (an
`answer:<question_key>` in `original_answers`, or a `document:<document_id>`
with extracted text), and its `quote` must appear verbatim (after whitespace
normalization) in that source's text. This is a truth check, not a schema
check — a citation can be well-shaped JSON and still be a hallucination.
"""

from __future__ import annotations

import re
import uuid

from nawa_api.ai.prompts.score_application import Citation

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


def citations_are_verbatim(
    citations: list[Citation],
    *,
    original_answers: dict[str, str],
    document_texts: dict[uuid.UUID, str] | None = None,
) -> bool:
    document_texts = document_texts or {}
    for citation in citations:
        source_text = _resolve_source(
            citation.source, original_answers=original_answers, document_texts=document_texts
        )
        if source_text is None:
            return False
        if _normalize_ws(citation.quote) not in _normalize_ws(source_text):
            return False
    return True
