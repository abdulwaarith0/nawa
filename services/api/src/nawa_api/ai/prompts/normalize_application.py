"""intake.normalize (SMALL). Skeleton — behavior fleshed in 06-intake-copilot.md."""

from pydantic import BaseModel, ConfigDict

from nawa_api.ai.prompts.base import PromptTemplate
from nawa_api.ai.types import Tier

SYSTEM = (
    "You normalize a raw application into clean sections without changing meaning. The text "
    "may be Arabic, English, or French. Preserve the source language verbatim — never "
    "translate. Do not invent content that is not present."
)


class NormalizeApplicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_text: str
    language: str


class NormalizeApplicationOutput(BaseModel):
    normalized_text: str


NORMALIZE_APPLICATION = PromptTemplate(
    task="intake.normalize",
    version="v1",
    tier=Tier.SMALL,
    input_schema=NormalizeApplicationInput,
    output_schema=NormalizeApplicationOutput,
    languages=("ar", "en", "fr"),
    system=SYSTEM,
    user_template="Language: {language}\n\nRaw application:\n{raw_text}",
)

# CHANGELOG:
# v1 (05-ai-infrastructure.md): initial skeleton — clean sectioning, no translation.
