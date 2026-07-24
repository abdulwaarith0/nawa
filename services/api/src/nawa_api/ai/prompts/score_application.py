"""intake.score (LARGE). 06-intake-copilot.md §3.1 — rubric-configurable
scoring with cited evidence.

The rubric text and application text are rendered by the caller (a
str.format template only accepts scalar fields), so this schema carries the
already-composed strings. Post-schema truth checks (citation keys/quotes
resolving verbatim against the real application) live in
services/intake/validate_scorecard.py, not here — a Pydantic schema can only
enforce shape, never truth.
"""

from pydantic import BaseModel, ConfigDict, Field

from nawa_api.ai.prompts.base import PromptTemplate
from nawa_api.ai.types import Tier

SYSTEM = (
    "You are a rubric scorer for an innovation-program intake. The application may be in "
    "Arabic, English, or French. Score EXACTLY the criteria given in the rubric — no more, no "
    "fewer, using the same criterion keys. For every criterion, cite the applicant's own words "
    "VERBATIM in the source language — a translated or paraphrased quote is not a citation, and "
    "a citation that cannot be found in the application will be rejected. Emit rationale prose "
    "bilingually in Arabic and English (never French). Score only against the supplied rubric; "
    "never decide acceptance — you rank and explain, a human decides."
)


class ScoreApplicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rubric: str  # rendered criteria: keys, weights, scale_max, bilingual guidance
    application_text: str  # original_answers (pseudonymized) + normalized summary


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str  # 'answer:<question_key>' or 'document:<document_id>' — 03's format
    quote: str  # VERBATIM, in the application's source language, never translated


class CriterionScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion_key: str
    score: int  # within the criterion's scale_max
    rationale_ar: str  # 2-5 sentences
    rationale_en: str
    citations: list[Citation] = Field(min_length=1)


class ScorecardDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criteria: list[CriterionScore]  # exactly the rubric's criterion keys, no more, no less
    rationale_ar: str  # overall rationale, both languages
    rationale_en: str
    confidence: float  # 0-1 self-reported confidence -> scorecards.confidence numeric(4,3)


SCORE_APPLICATION = PromptTemplate(
    task="intake.score",
    version="v2",
    tier=Tier.LARGE,
    input_schema=ScoreApplicationInput,
    output_schema=ScorecardDraft,
    languages=("ar", "en", "fr"),
    system=SYSTEM,
    user_template="Rubric:\n{rubric}\n\nApplication:\n{application_text}",
)

# CHANGELOG:
# v1 (05-ai-infrastructure.md): initial skeleton — weighted rubric scoring with per-criterion
#     verbatim citations; AR/EN/FR input, bilingual AR+EN rationale output.
# v2 (06-intake-copilot.md §3.1): real §3 shape. ScoreApplicationInput carries rendered
#     rubric/application_text strings (not raw lists — the template engine only fills
#     scalars). ScorecardDraft drops the model-computed `overall` (Python computes the
#     weighted total from rubric weights so we never trust model arithmetic) and adds
#     `confidence`. Citation is now {source, quote} matching 03's scorecard_criteria.citations
#     jsonb shape exactly, with `source` naming the answer/document the quote came from so a
#     hallucinated quote can be caught by exact substring match.
