"""intake.hidden_gem (LARGE). 06-intake-copilot.md §5 — a distinct second pass
over low scorers: substance over presentation.

The failure mode this exists to prevent: a strong idea written poorly — rural
applicants, non-native writers — dies in a keyword filter or a low
presentation-weighted score. There is no separate "potential score" field —
if the model judges the idea would score materially higher than the
presentation did, that assessment is written directly into the reason text.
"""

from pydantic import BaseModel, ConfigDict, Field

from nawa_api.ai.prompts.base import PromptTemplate
from nawa_api.ai.prompts.score_application import Citation
from nawa_api.ai.types import Tier

SYSTEM = (
    "You review a LOW-SCORING innovation-program application for a strong idea buried under weak "
    "presentation. Ignore grammar, spelling, structure, and register entirely — assess the "
    "underlying idea's novelty and feasibility as if it had been written fluently. Be especially "
    "attentive to applications whose source language is not English or that show non-native "
    "phrasing; a rural applicant or non-native writer must never be penalized for prose. If you "
    "judge the underlying idea would score materially higher than the presentation did, say so "
    "explicitly in the reason text (e.g. 'the idea itself would merit roughly 8/10 on novelty "
    "because...') — there is no separate potential-score field. Cite the applicant's own words "
    "VERBATIM in the source language — a translated or paraphrased quote is not a citation. "
    "Explain bilingually in Arabic and English. You flag for human attention; you never accept, "
    "reject, or change the score."
)


class HiddenGemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    application_text: str


class HiddenGemReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_hidden_gem: bool
    reason_ar: str
    reason_en: str
    citations: list[Citation] = Field(min_length=1)


HIDDEN_GEM_REVIEW = PromptTemplate(
    task="intake.hidden_gem",
    version="v2",
    tier=Tier.LARGE,
    input_schema=HiddenGemInput,
    output_schema=HiddenGemReview,
    languages=("ar", "en", "fr"),
    system=SYSTEM,
    user_template="Application:\n{application_text}",
)

# CHANGELOG:
# v1 (05-ai-infrastructure.md): initial skeleton — {is_gem, reasoning_ar, reasoning_en}, no
#     citations.
# v2 (06-intake-copilot.md §5): real shape — {is_hidden_gem, reason_ar, reason_en, citations}
#     matching 03's scorecards.hidden_gem_reason_ar/_en columns; citations share the same
#     verbatim-citation contract as scoring (services/intake/_citations.py).
