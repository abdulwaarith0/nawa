"""PROMPT_REGISTRY — every template registered here (05-ai-infrastructure.md §6).

Templates are discovered by scanning each task module for PromptTemplate
instances, so adding a task file is enough to register it. TEMPLATE_FILES maps
each task to its defining file for the CHANGELOG audit test.
"""

from __future__ import annotations

from types import ModuleType

from nawa_api.ai.prompts import (
    detect_language,
    hidden_gem_review,
    normalize_application,
    rag_answer,
    score_application,
)
from nawa_api.ai.prompts.base import PromptTemplate

_MODULES: tuple[ModuleType, ...] = (
    detect_language,
    normalize_application,
    score_application,
    hidden_gem_review,
    rag_answer,
)

PROMPT_REGISTRY: dict[str, PromptTemplate] = {}
TEMPLATE_FILES: dict[str, str] = {}

for _mod in _MODULES:
    for _value in vars(_mod).values():
        if isinstance(_value, PromptTemplate):
            if _value.task in PROMPT_REGISTRY:
                raise RuntimeError(f"duplicate prompt task registered: {_value.task}")
            PROMPT_REGISTRY[_value.task] = _value
            TEMPLATE_FILES[_value.task] = _mod.__file__


def get_template(task: str) -> PromptTemplate:
    return PROMPT_REGISTRY[task]
