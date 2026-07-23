"""intake.hidden_gem (LARGE). Skeleton — behavior fleshed in 06-intake-copilot.md."""

from pydantic import BaseModel, ConfigDict

from nawa_api.ai.prompts.base import PromptTemplate
from nawa_api.ai.types import Tier

SYSTEM = (
    "You look past weak phrasing, non-native language, or poor structure to judge whether a "
    "low-scoring application hides a strong idea (a 'hidden gem'). Input may be Arabic, "
    "English, or French. Cite the applicant's own words VERBATIM in the source language. "
    "Explain bilingually in Arabic and English. You flag for human attention; you never "
    "accept or reject."
)


class HiddenGemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    application_text: str


class HiddenGemReview(BaseModel):
    is_gem: bool
    reasoning_ar: str
    reasoning_en: str


HIDDEN_GEM_REVIEW = PromptTemplate(
    task="intake.hidden_gem",
    version="v1",
    tier=Tier.LARGE,
    input_schema=HiddenGemInput,
    output_schema=HiddenGemReview,
    languages=("ar", "en", "fr"),
    system=SYSTEM,
    user_template="Application:\n{application_text}",
)

# CHANGELOG:
# v1 (05-ai-infrastructure.md): initial skeleton — hidden-gem recall over weak-phrasing apps.
