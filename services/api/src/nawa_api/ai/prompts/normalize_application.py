"""intake.normalize (SMALL) — 06-intake-copilot.md §2.2."""

from pydantic import BaseModel, ConfigDict

from nawa_api.ai.prompts.base import PromptTemplate
from nawa_api.ai.types import Tier

SYSTEM = (
    "You produce a structured English projection of a raw application so it can be displayed and "
    "embedded. The source text may be Arabic, English, or French. Do not invent content that is "
    "not present; where a field is unknown, use an empty string. Return exactly the fields of the "
    "schema. The applicant's verbatim submission is preserved separately and is never replaced by "
    "this projection."
)


class NormalizeApplicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_text: str
    language: str


class NormalizeApplicationOutput(BaseModel):
    title: str
    summary: str
    problem: str
    solution: str
    team: str
    field: str
    country: str
    notable: str


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
# v1 (06-intake-copilot.md): structured EN projection —
#     {title, summary, problem, solution, team, field, country, notable} (03's normalized shape).
