"""intake.detect_language (SMALL). Skeleton — behavior fleshed in 06-intake-copilot.md."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from nawa_api.ai.prompts.base import PromptTemplate
from nawa_api.ai.types import Tier

SYSTEM = (
    "You detect the dominant natural language of applicant-submitted text, which may be "
    "Arabic, English, or French. Return only the detected language code and a confidence "
    "between 0 and 1. Do not translate or summarize the text."
)


class DetectLanguageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


class DetectLanguageOutput(BaseModel):
    language: Literal["ar", "en", "fr"]
    confidence: float


DETECT_LANGUAGE = PromptTemplate(
    task="intake.detect_language",
    version="v1",
    tier=Tier.SMALL,
    input_schema=DetectLanguageInput,
    output_schema=DetectLanguageOutput,
    languages=("ar", "en", "fr"),
    system=SYSTEM,
    user_template="Text:\n{text}",
    max_tokens=256,
)

# CHANGELOG:
# v1 (05-ai-infrastructure.md): initial skeleton — detect ar/en/fr of application text.
