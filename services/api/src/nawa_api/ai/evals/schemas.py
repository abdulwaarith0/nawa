"""Golden-dataset + ground-truth schemas (05-ai-infrastructure.md §10).

This slice defines the format + a small smoke sample; 06-intake-copilot.md
authors the full datasets derived from the seed corpus.
"""

from __future__ import annotations

from statistics import mean
from typing import Literal

from pydantic import BaseModel


class ScoredEntry(BaseModel):
    application_ref: str
    text: str
    human_scores: dict[str, float]
    human_rank_band: str
    language: Literal["ar", "en", "fr"]
    country: str
    gender: str
    origin: Literal["urban", "rural"]

    def human_overall(self) -> float:
        return mean(self.human_scores.values()) if self.human_scores else 0.0


class HiddenGemEntry(BaseModel):
    application_ref: str
    text: str
    is_gem: bool


class GroundTruth(BaseModel):
    """Seeded answer key stored in site_config under `seed:ground_truth`."""

    hidden_gem_ids: list[str] = []
    dedup_pair_ids: list[list[str]] = []
    anomaly_profile_ids: list[str] = []
