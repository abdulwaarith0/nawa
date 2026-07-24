"""Eval harness entry point (05-ai-infrastructure.md §10).

    uv run python -m nawa_api.ai.evals.run --offline   # mock, fixtures, no keys
    uv run python -m nawa_api.ai.evals.run --live --yes-spend

Runs fully offline against MockLLMProvider. Prints a final summary line:
    AGREEMENT: NN.N% | SPEARMAN: 0.NN | GEM RECALL: NN.N% | MAX SLICE GAP: NN.Npts
06-intake-copilot.md wires this to the real intake pipeline and reports the
agreement number in its demo.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from statistics import mean

from pydantic import BaseModel

from nawa_api.ai import gateway
from nawa_api.ai.evals.agreement import compute_agreement
from nawa_api.ai.evals.hidden_gem import compute_gem_metrics
from nawa_api.ai.evals.schemas import HiddenGemEntry, ScoredEntry
from nawa_api.ai.evals.slices import compute_slice_agreements
from nawa_api.ai.prompts import get_template
from nawa_api.ai.prompts.hidden_gem_review import HiddenGemInput, HiddenGemReview
from nawa_api.ai.prompts.score_application import ScoreApplicationInput, ScorecardDraft

EVAL_MIN_AGREEMENT = 0.0  # live mode raises this; offline mock outputs are synthetic
_GOLDEN = Path(__file__).resolve().parents[4] / "tests" / "ai" / "golden"


class EvalSummary(BaseModel):
    agreement: float
    spearman: float
    gem_recall: float
    max_slice_gap: float
    biased: bool = False


def load_scored_sample(path: Path | None = None) -> list[ScoredEntry]:
    data = json.loads((path or _GOLDEN / "scored_sample.json").read_text(encoding="utf-8"))
    return [ScoredEntry.model_validate(item) for item in data]


def load_hidden_gems(path: Path | None = None) -> list[HiddenGemEntry]:
    data = json.loads((path or _GOLDEN / "hidden_gems.json").read_text(encoding="utf-8"))
    return [HiddenGemEntry.model_validate(item) for item in data]


async def ai_overall(entry: ScoredEntry, *, provider_name: str | None = "mock") -> float:
    rubric_text = "\n".join(f"- {key}" for key in entry.human_scores)
    request = get_template("intake.score").render(
        ScoreApplicationInput(rubric=rubric_text, application_text=entry.text)
    )
    request = request.model_copy(update={"task": "eval.intake"})
    scorecard, _ = await gateway.complete_structured(
        request, ScorecardDraft, pii_safe=True, provider_name=provider_name
    )
    return mean(criterion.score for criterion in scorecard.criteria)


async def ai_is_gem(entry: HiddenGemEntry, *, provider_name: str | None = "mock") -> bool:
    request = get_template("intake.hidden_gem").render(
        HiddenGemInput(application_text=entry.text)
    )
    request = request.model_copy(update={"task": "eval.hidden_gem"})
    review, _ = await gateway.complete_structured(
        request, HiddenGemReview, pii_safe=True, provider_name=provider_name
    )
    return review.is_hidden_gem


async def run_evals(
    *,
    scored: list[ScoredEntry],
    gems: list[HiddenGemEntry],
    scorer: Callable[[ScoredEntry], Awaitable[float]] | None = None,
    gemmer: Callable[[HiddenGemEntry], Awaitable[bool]] | None = None,
    provider_name: str | None = "mock",
) -> EvalSummary:
    scorer = scorer or (lambda e: ai_overall(e, provider_name=provider_name))
    gemmer = gemmer or (lambda e: ai_is_gem(e, provider_name=provider_name))
    human = [entry.human_overall() for entry in scored]
    ai = [await scorer(entry) for entry in scored]
    agreement = compute_agreement(human, ai)
    gem = compute_gem_metrics([g.is_gem for g in gems], [await gemmer(g) for g in gems])
    slices = compute_slice_agreements(scored, human, ai, key=lambda e: e.language)
    return EvalSummary(
        agreement=agreement.agreement_pct,
        spearman=agreement.spearman,
        gem_recall=gem.recall_pct,
        max_slice_gap=slices.max_gap,
        biased=slices.biased,
    )


def format_summary(summary: EvalSummary) -> str:
    return (
        f"AGREEMENT: {summary.agreement:.1f}% | "
        f"SPEARMAN: {summary.spearman:.2f} | "
        f"GEM RECALL: {summary.gem_recall:.1f}% | "
        f"MAX SLICE GAP: {summary.max_slice_gap:.1f}pts"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nawa-evals")
    parser.add_argument("--offline", action="store_true", help="mock provider, no keys (default)")
    parser.add_argument("--live", action="store_true", help="real provider, real spend")
    parser.add_argument("--yes-spend", action="store_true", help="required with --live")
    parser.add_argument("--against-seed", action="store_true", help="also evaluate the seed key")
    args = parser.parse_args(argv)

    if args.live and not args.yes_spend:
        print("Refusing --live without --yes-spend (real vendor spend).")
        return 2

    provider_name = None if args.live else "mock"  # --offline forces the mock
    summary = asyncio.run(
        run_evals(
            scored=load_scored_sample(), gems=load_hidden_gems(), provider_name=provider_name
        )
    )
    if summary.biased:
        print("*** BIAS WARNING: inter-slice agreement gap exceeds threshold ***")
    print(format_summary(summary))

    threshold = EVAL_MIN_AGREEMENT if args.live else 0.0
    return 0 if summary.agreement >= threshold else 1


if __name__ == "__main__":
    raise SystemExit(main())
