"""Versioned prompt registry primitives (05-ai-infrastructure.md §6).

A prompt change is a behavior change and must be reviewable like code. Each task
gets one file declaring a PromptTemplate with static system text, a
str.format-style user template, and input/output Pydantic schemas. render()
validates input and stamps task+version onto an LLMRequest; fingerprint() is the
template's identity, used by the CHANGELOG test.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from pydantic import BaseModel

from nawa_api.ai.types import LLMRequest, Tier


@dataclass(frozen=True)
class PromptTemplate:
    task: str  # dot-namespaced per 03's ai_calls.task vocabulary
    version: str  # e.g. "v1" — bumping behavior means bumping this + a CHANGELOG line
    tier: Tier
    input_schema: type[BaseModel]  # what render() accepts
    output_schema: type[BaseModel]  # what complete_structured() returns
    languages: tuple[str, ...]  # languages handled in the APPLICATION text
    system: str  # static string — NO f-strings with volatile values
    user_template: str  # str.format-style with declared placeholders only
    max_tokens: int = 4096

    def render(self, data: BaseModel | dict) -> LLMRequest:
        """Validate the input against input_schema, fill the user template, and
        stamp task + prompt_version. Missing or extra fields raise immediately."""
        if isinstance(data, dict):
            model = self.input_schema.model_validate(data)
        elif isinstance(data, self.input_schema):
            model = data
        else:
            raise TypeError(
                f"{self.task} expects {self.input_schema.__name__}, got {type(data).__name__}"
            )
        content = self.user_template.format(**model.model_dump())
        return LLMRequest(
            task=self.task,
            prompt_version=self.version,
            tier=self.tier,
            system=self.system,
            messages=[{"role": "user", "content": content}],
            max_tokens=self.max_tokens,
        )

    def fingerprint(self) -> str:
        """Template identity: sha256(system + user_template + version)[:16].
        Distinct from ai_calls.prompt_hash (the per-call rendered+pseudonymized
        payload hash the gateway logs)."""
        raw = self.system + self.user_template + self.version
        return sha256(raw.encode("utf-8")).hexdigest()[:16]
