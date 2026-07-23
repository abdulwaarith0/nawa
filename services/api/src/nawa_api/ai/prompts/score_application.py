"""intake.score (LARGE). Skeleton — full rubric behavior fleshed in 06-intake-copilot.md."""

from pydantic import BaseModel, ConfigDict

from nawa_api.ai.prompts.base import PromptTemplate
from nawa_api.ai.types import Tier

SYSTEM = (
    "You are a rubric scorer for an innovation-program intake. The application may be in "
    "Arabic, English, or French. For every criterion, cite the applicant's own words "
    "VERBATIM in the source language — a translated quote is not a citation. Emit rationale "
    "prose bilingually in Arabic and English (never French). Score only against the supplied "
    "rubric; never decide acceptance — you rank and explain, a human decides."
)


class ScoreApplicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rubric: str
    criteria: list[str]
    application_text: str


class CriterionScore(BaseModel):
    criterion: str
    score: float
    citation: str  # verbatim, source-language quote


class ScorecardDraft(BaseModel):
    scores: list[CriterionScore]
    overall: float
    rationale_ar: str
    rationale_en: str


SCORE_APPLICATION = PromptTemplate(
    task="intake.score",
    version="v1",
    tier=Tier.LARGE,
    input_schema=ScoreApplicationInput,
    output_schema=ScorecardDraft,
    languages=("ar", "en", "fr"),
    system=SYSTEM,
    user_template="Rubric:\n{rubric}\n\nCriteria: {criteria}\n\nApplication:\n{application_text}",
)

# CHANGELOG:
# v1 (05-ai-infrastructure.md): initial skeleton — weighted rubric scoring with per-criterion
#     verbatim citations; AR/EN/FR input, bilingual AR+EN rationale output.
