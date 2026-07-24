"""DoD spot-check (06-intake-copilot.md DoD #4): every persisted AI-sourced
scorecard_criteria.citations entry must resolve verbatim against the citing
application's own original_answers (or an attached document's extracted
text) — the same truth check services/intake/_citations.py already enforces
before a scorecard is ever persisted. This script re-checks the CURRENTLY
PERSISTED rows directly against the database, independent of that runtime
check, as an auditable proof rather than a repeat of the same code path.

Scoped to `scorecards.source = 'ai'` only: the verbatim-citation contract is
specifically an AI-hallucination guard (never applied to `source='human'`
rows anywhere in the codebase — e.g. seed_data/applications.py's Season-17
jury scorecards cite `{"source": "answer:q1_problem", "quote": "reviewed"}`,
a human reviewer's shorthand note, not a claim that "reviewed" appears
verbatim in the application).

Usage: uv run python -m nawa_api.scripts.verify_citations
Exits 1 (and prints every offending row) if any citation fails to resolve.
"""

import asyncio
import sys

from sqlalchemy import select

import nawa_api  # noqa: F401  (Windows event-loop policy)
from nawa_api.models.intake import Application, ApplicationDocument, Scorecard, ScorecardCriterion
from nawa_api.runtime.postgres import session_factory
from nawa_api.services.intake._citations import citations_are_verbatim


class _Citation:
    def __init__(self, source: str, quote: str) -> None:
        self.source = source
        self.quote = quote


async def verify() -> tuple[int, int, list[str]]:
    """Returns (total_criteria_checked, failing_count, failing_descriptions)."""
    async with session_factory() as session:
        ai_scorecards = (
            (await session.execute(select(Scorecard).where(Scorecard.source == "ai")))
            .scalars()
            .all()
        )
        ai_scorecard_ids = {sc.id for sc in ai_scorecards}
        criteria = (
            (
                await session.execute(
                    select(ScorecardCriterion).where(
                        ScorecardCriterion.scorecard_id.in_(ai_scorecard_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        total = len(criteria)
        failing: list[str] = []

        app_id_by_scorecard = {sc.id: sc.application_id for sc in ai_scorecards}
        application_ids = set(app_id_by_scorecard.values())
        applications = (
            (
                await session.execute(
                    select(Application).where(Application.id.in_(application_ids))
                )
            )
            .scalars()
            .all()
        )
        answers_by_application = {a.id: a.original_answers for a in applications}
        documents = (
            (
                await session.execute(
                    select(ApplicationDocument).where(
                        ApplicationDocument.application_id.in_(application_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        doc_texts_by_application: dict = {}
        for doc in documents:
            if doc.extracted_text:
                doc_texts_by_application.setdefault(doc.application_id, {})[doc.id] = (
                    doc.extracted_text
                )

        for criterion in criteria:
            application_id = app_id_by_scorecard.get(criterion.scorecard_id)
            original_answers = answers_by_application.get(application_id, {})
            document_texts = doc_texts_by_application.get(application_id, {})
            citation_objs = [_Citation(c["source"], c["quote"]) for c in criterion.citations]
            if not citations_are_verbatim(
                citation_objs, original_answers=original_answers, document_texts=document_texts
            ):
                failing.append(
                    f"scorecard_criteria.id={criterion.id} criterion_key={criterion.criterion_key} "
                    f"application_id={application_id}"
                )
        return total, len(failing), failing


def main() -> int:
    total, failing_count, failing = asyncio.run(verify())
    print(f"Checked {total} scorecard_criteria rows; {failing_count} non-matching quote(s).")
    for line in failing:
        print(f"  FAIL: {line}")
    return 1 if failing_count else 0


if __name__ == "__main__":
    sys.exit(main())
