"""assistant.answer (LARGE). Citation-bearing RAG answers (05-ai-infrastructure.md §9.4)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from nawa_api.ai.prompts.base import PromptTemplate
from nawa_api.ai.types import Tier

SYSTEM = (
    "You answer questions using ONLY the numbered source chunks provided. Tie every claim to "
    "the chunk it came from via its id. Quote source text VERBATIM in its original language. "
    "If the chunks do not support an answer, say so — never free-associate. Answer in Arabic "
    "or English matching the question's language; never in French."
)


class RagAnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str
    context: str  # numbered [1]..[k] chunks with their ids


class Citation(BaseModel):
    chunk_id: int
    quote: str


class RagAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: Literal["supported", "unsupported"]


RAG_ANSWER = PromptTemplate(
    task="assistant.answer",
    version="v1",
    tier=Tier.LARGE,
    input_schema=RagAnswerInput,
    output_schema=RagAnswer,
    languages=("ar", "en"),
    system=SYSTEM,
    user_template="Question:\n{question}\n\nSources:\n{context}",
)

# CHANGELOG:
# v1 (05-ai-infrastructure.md): initial version — citation-required answers with a
#     supported/unsupported confidence flag for the amber "no source" UI treatment.
