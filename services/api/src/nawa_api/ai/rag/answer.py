"""Citation-bearing answer assembly (05-ai-infrastructure.md §9.4).

Retrieved chunks are numbered [1]..[k]; the model must cite by number, and every
cited number is validated against the retrieved set — a hallucinated id is
dropped. An answer with zero surviving citations is returned as "unsupported" so
the UI renders the amber "AI-generated, no source" treatment.
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from nawa_api.ai import gateway
from nawa_api.ai.prompts import get_template
from nawa_api.ai.prompts.rag_answer import RagAnswer, RagAnswerInput
from nawa_api.ai.rag.retrieve import RetrievalFilters, retrieve

_NO_SOURCE = "No supporting source was found for this question."


class ResolvedCitation(BaseModel):
    chunk_id: uuid.UUID
    quote: str


class AnswerResult(BaseModel):
    answer: str
    citations: list[ResolvedCitation] = Field(default_factory=list)
    confidence: Literal["supported", "unsupported"]


def _build_context(chunks) -> str:
    return "\n".join(
        f"[{index}] (chunk {chunk.chunk_id}) {chunk.content}"
        for index, chunk in enumerate(chunks, start=1)
    )


async def answer_question(
    question: str,
    *,
    filters: RetrievalFilters | None = None,
    k: int = 8,
    created_by: uuid.UUID | None = None,
) -> AnswerResult:
    chunks = await retrieve(question, k=k, filters=filters)
    if not chunks:
        return AnswerResult(answer=_NO_SOURCE, citations=[], confidence="unsupported")

    request = get_template("assistant.answer").render(
        RagAnswerInput(question=question, context=_build_context(chunks))
    )
    result: RagAnswer
    result, _ = await gateway.complete_structured(
        request, RagAnswer, pii_safe=True, created_by=created_by
    )

    # Validate cited [n] numbers against the retrieved set; drop hallucinations.
    resolved = [
        ResolvedCitation(chunk_id=chunks[citation.chunk_id - 1].chunk_id, quote=citation.quote)
        for citation in result.citations
        if 1 <= citation.chunk_id <= len(chunks)
    ]
    confidence: Literal["supported", "unsupported"] = "supported" if resolved else "unsupported"
    return AnswerResult(answer=result.answer, citations=resolved, confidence=confidence)
