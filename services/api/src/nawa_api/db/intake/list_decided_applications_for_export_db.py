import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Application, Decision, Scorecard
from nawa_api.utils.logger import get_logger

_DECIDED_STATUSES = ("shortlisted", "waitlisted", "decided")

ExportRow = tuple[Application, Scorecard | None, dict | None]


async def list_decided_applications_for_export_db(
    *, cycle_id: uuid.UUID, rubric_id: uuid.UUID | None, session: AsyncSession | None = None
) -> list[ExportRow]:
    """The decided shortlist (06-intake-copilot.md §6.1's export): every
    application past `scored` — i.e. one a human has actually decided on —
    ranked by ai_total_score desc, paired with its current-rubric AI
    scorecard and its LATEST decision (DISTINCT ON, one per application) as
    a plain dict `{decision, reason, decided_by, created_at}` so the export
    can show reason/decider/decided_at, not just a status string.
    `rubric_id=None` (no active rubric on the program) intentionally matches
    no scorecard — `Scorecard.rubric_id` is NOT NULL, so `== None` compiles
    to `IS NULL`, which never matches a real row."""
    with observe_db(
        operation="read",
        table="applications",
        method="list_decided_applications_for_export_db",
    ) as obs:
        try:
            latest_decision = (
                select(
                    Decision.application_id,
                    Decision.decision,
                    Decision.reason,
                    Decision.decided_by,
                    Decision.created_at,
                )
                .distinct(Decision.application_id)
                .order_by(Decision.application_id, Decision.created_at.desc())
                .subquery()
            )

            stmt = (
                select(
                    Application,
                    Scorecard,
                    latest_decision.c.decision,
                    latest_decision.c.reason,
                    latest_decision.c.decided_by,
                    latest_decision.c.created_at,
                )
                .outerjoin(
                    Scorecard,
                    and_(
                        Scorecard.application_id == Application.id,
                        Scorecard.rubric_id == rubric_id,
                        Scorecard.source == "ai",
                    ),
                )
                .outerjoin(
                    latest_decision, latest_decision.c.application_id == Application.id
                )
                .where(
                    Application.cycle_id == cycle_id,
                    Application.status.in_(_DECIDED_STATUSES),
                )
                .order_by(Application.ai_total_score.desc().nulls_last())
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).all()
            obs.success = True
            results: list[ExportRow] = []
            for application, scorecard, decision, reason, decided_by, decided_at in rows:
                decision_info = (
                    {
                        "decision": decision,
                        "reason": reason,
                        "decided_by": decided_by,
                        "created_at": decided_at,
                    }
                    if decision is not None
                    else None
                )
                results.append((application, scorecard, decision_info))
            return results
        except Exception:
            get_logger().warning(
                "db_error", method="list_decided_applications_for_export_db", exc_info=True
            )
            obs.success = False
            return []
