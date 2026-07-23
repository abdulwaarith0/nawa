"""AI-vs-human agreement metrics (05-ai-infrastructure.md §10). Pure functions."""

from __future__ import annotations

from pydantic import BaseModel


class AgreementResult(BaseModel):
    agreement_pct: float  # top-quartile agreement
    spearman: float
    mean_delta: float


def _ranks(values: list[float]) -> list[float]:
    """Average ranks (1-based), ties shared."""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def top_quartile_agreement(human: list[float], ai: list[float]) -> float:
    """Of the humans' top 25%, the fraction the AI also ranks top 25%."""
    n = len(human)
    if n == 0:
        return 0.0
    q = max(1, n // 4)

    def top_set(scores: list[float]) -> set[int]:
        return set(sorted(range(n), key=lambda i: scores[i], reverse=True)[:q])

    human_top = top_set(human)
    ai_top = top_set(ai)
    return len(human_top & ai_top) / len(human_top) * 100


def spearman(human: list[float], ai: list[float]) -> float:
    n = len(human)
    if n < 2:
        return 0.0
    rh, ra = _ranks(human), _ranks(ai)
    d2 = sum((rh[i] - ra[i]) ** 2 for i in range(n))
    denom = n * (n * n - 1)
    return 1 - 6 * d2 / denom if denom else 0.0


def mean_abs_delta(human: list[float], ai: list[float]) -> float:
    if not human:
        return 0.0
    return sum(abs(h - a) for h, a in zip(human, ai, strict=False)) / len(human)


def compute_agreement(human: list[float], ai: list[float]) -> AgreementResult:
    return AgreementResult(
        agreement_pct=top_quartile_agreement(human, ai),
        spearman=spearman(human, ai),
        mean_delta=mean_abs_delta(human, ai),
    )
