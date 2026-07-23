"""Hidden-gem recall + false-positive metrics (05-ai-infrastructure.md §10)."""

from __future__ import annotations

from pydantic import BaseModel


class GemResult(BaseModel):
    recall_pct: float  # gems flagged / gems present
    false_positive_pct: float  # controls wrongly flagged / controls present


def compute_gem_metrics(labels: list[bool], predictions: list[bool]) -> GemResult:
    gems = [i for i, is_gem in enumerate(labels) if is_gem]
    controls = [i for i, is_gem in enumerate(labels) if not is_gem]
    recall = 100 * sum(predictions[i] for i in gems) / len(gems) if gems else 0.0
    fp = 100 * sum(predictions[i] for i in controls) / len(controls) if controls else 0.0
    return GemResult(recall_pct=recall, false_positive_pct=fp)
