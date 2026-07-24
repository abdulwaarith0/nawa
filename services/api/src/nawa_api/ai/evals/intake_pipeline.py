"""Wires the eval harness to the REAL intake pipeline (06-intake-copilot.md
§8) — not a shortcut path. For each golden entry this builds a throwaway
application against a dedicated, isolated rubric/cycle/program (created once
per run, torn down afterward — "the eval never touches the dev database's
real cycle data"), then calls the ACTUAL `score_application` / hidden-gem
`_review_one` job functions through the gateway, and reads back whatever
they persisted.

Offline (MockLLMProvider) note: the mock's synthesized citations and
criterion keys can never satisfy `validate_scorecard`/
`validate_hidden_gem_review`'s verbatim-citation and criterion-key checks —
so every entry legitimately fails validation and falls back to 0.0 / "not a
gem" offline. That is the HONEST result of running the real,
validation-gated pipeline through a provider that cannot produce compliant
structured output — it proves the wiring, per spec's own framing ("Offline
mode proves the wiring; the numbers become meaningful in --live mode"), not
a bug to work around.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete

from nawa_api.ai.evals.schemas import HiddenGemEntry, ScoredEntry
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.get_application_db import get_application_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.utils import in_transaction
from nawa_api.jobs.hidden_gem_scan import _review_one
from nawa_api.jobs.score_applications import score_application
from nawa_api.models.intake import Application, Rubric
from nawa_api.models.programs import Program, ProgramCycle
from nawa_api.seed_data.programs import SOS_RUBRIC_CRITERIA

_EVAL_TASK = "eval.intake"


class EvalFixture:
    """One shared program/cycle/rubric for a whole eval run — created in
    `__aenter__`, deleted in `__aexit__` (in FK-safe order: applications
    first via CASCADE, then rubric, then cycle, then program)."""

    def __init__(self) -> None:
        self.program_id: uuid.UUID | None = None
        self.cycle_id: uuid.UUID | None = None
        self.rubric_id: uuid.UUID | None = None

    async def __aenter__(self) -> EvalFixture:
        program = await create_program_db(
            slug=f"eval-intake-{uuid.uuid4().hex[:8]}", kind="competition", name_en="Eval Program"
        )
        cycle = await create_program_cycle_db(
            program_id=program.id, slug=f"eval-cycle-{uuid.uuid4().hex[:8]}", name_en="Eval Cycle"
        )
        rubric = await create_rubric_db(
            program_id=program.id,
            version=1,
            criteria=SOS_RUBRIC_CRITERIA,
            name_en="Eval Rubric",
            status="active",
        )
        self.program_id, self.cycle_id, self.rubric_id = program.id, cycle.id, rubric.id
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        async with in_transaction() as session:
            await session.execute(delete(Application).where(Application.cycle_id == self.cycle_id))
            await session.execute(delete(Rubric).where(Rubric.id == self.rubric_id))
            await session.execute(delete(ProgramCycle).where(ProgramCycle.id == self.cycle_id))
            await session.execute(delete(Program).where(Program.id == self.program_id))


async def _create_throwaway_application(
    *, cycle_id: uuid.UUID, text: str, language: str
) -> uuid.UUID:
    app = await create_application_db(
        cycle_id=cycle_id,
        applicant_name="Golden Entry",
        applicant_email=f"golden-{uuid.uuid4().hex[:8]}@eval.nawa.local",
        source_language=language,
        original_answers={"idea": text},
    )
    return app.id


async def ai_overall_intake(
    entry: ScoredEntry, *, fixture: EvalFixture, provider_name: str | None = "mock"
) -> float:
    application_id = await _create_throwaway_application(
        cycle_id=fixture.cycle_id, text=entry.text, language=entry.language
    )
    try:
        await score_application(
            application_id=application_id,
            rubric_id=fixture.rubric_id,
            cycle_id=fixture.cycle_id,
            provider_name=provider_name,
            task_override=_EVAL_TASK,
        )
        application = await get_application_db(application_id=application_id)
        return application.ai_total_score if application and application.ai_total_score else 0.0
    finally:
        async with in_transaction() as session:
            await session.execute(delete(Application).where(Application.id == application_id))


async def ai_is_gem_intake(
    entry: HiddenGemEntry, *, fixture: EvalFixture, provider_name: str | None = "mock"
) -> bool:
    # HiddenGemEntry carries no language field (schemas.py) — the throwaway
    # row's source_language isn't read by _review_one's own logic at all, so
    # any valid value is harmless here.
    application_id = await _create_throwaway_application(
        cycle_id=fixture.cycle_id, text=entry.text, language="en"
    )
    try:
        application = await get_application_db(application_id=application_id)
        review = await _review_one(
            application,
            cycle_id=fixture.cycle_id,
            provider_name=provider_name,
            task_override=_EVAL_TASK,
        )
        return review.is_hidden_gem if review is not None else False
    finally:
        async with in_transaction() as session:
            await session.execute(delete(Application).where(Application.id == application_id))
