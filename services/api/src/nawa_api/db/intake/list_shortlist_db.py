import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import clamp_pagination, use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Application, Decision, DedupMatch, Scorecard, ScorecardCriterion
from nawa_api.utils.logger import get_logger

ShortlistRow = tuple[Application, Scorecard | None, str | None]


async def list_shortlist_db(
    *,
    cycle_id: uuid.UUID,
    rubric_id: uuid.UUID,
    score_min: float | None = None,
    score_max: float | None = None,
    criterion: str | None = None,
    criterion_min: float | None = None,
    flags: frozenset[str] = frozenset(),
    language: str | None = None,
    country: str | None = None,
    decision: str | None = None,
    q: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    session: AsyncSession | None = None,
) -> list[ShortlistRow]:
    """Ranked by ai_total_score desc against the CURRENT rubric version (the
    caller resolves `rubric_id` from the cycle's active rubric). Every filter
    is combinable, per 06-intake-copilot.md §6.1. `decision` is derived from
    `Application.status` for shortlist/waitlist/undecided, and from the
    latest `decisions` row (DISTINCT ON, one row per application) for the
    'decided' status's two outcomes (reject/accept)."""
    clamped_limit, clamped_offset = clamp_pagination(limit=limit, offset=offset)
    with observe_db(operation="read", table="applications", method="list_shortlist_db") as obs:
        try:
            latest_decision = (
                select(Decision.application_id, Decision.decision)
                .distinct(Decision.application_id)
                .order_by(Decision.application_id, Decision.created_at.desc())
                .subquery()
            )

            stmt = (
                select(Application, Scorecard, latest_decision.c.decision)
                .outerjoin(
                    Scorecard,
                    and_(
                        Scorecard.application_id == Application.id,
                        Scorecard.rubric_id == rubric_id,
                        Scorecard.source == "ai",
                    ),
                )
                .outerjoin(latest_decision, latest_decision.c.application_id == Application.id)
                .where(Application.cycle_id == cycle_id)
            )

            if criterion is not None and criterion_min is not None:
                stmt = stmt.join(
                    ScorecardCriterion,
                    and_(
                        ScorecardCriterion.scorecard_id == Scorecard.id,
                        ScorecardCriterion.criterion_key == criterion,
                        ScorecardCriterion.score >= criterion_min,
                    ),
                )
            if score_min is not None:
                stmt = stmt.where(Application.ai_total_score >= score_min)
            if score_max is not None:
                stmt = stmt.where(Application.ai_total_score <= score_max)
            if "hidden_gem" in flags:
                stmt = stmt.where(Scorecard.hidden_gem.is_(True))
            if "normalize_failed" in flags:
                stmt = stmt.where(Application.status == "normalize_failed")
            if "dedup_pending" in flags:
                stmt = stmt.where(
                    select(DedupMatch.id)
                    .where(
                        or_(
                            DedupMatch.application_id == Application.id,
                            DedupMatch.matched_application_id == Application.id,
                        ),
                        DedupMatch.status == "pending",
                    )
                    .exists()
                )
            if language is not None:
                stmt = stmt.where(Application.source_language == language)
            if country is not None:
                stmt = stmt.where(Application.normalized["country"].astext == country)
            if q is not None:
                like = f"%{q}%"
                stmt = stmt.where(
                    or_(Application.title.ilike(like), Application.summary.ilike(like))
                )
            if decision == "undecided":
                stmt = stmt.where(Application.status == "scored")
            elif decision == "shortlist":
                stmt = stmt.where(Application.status == "shortlisted")
            elif decision == "waitlist":
                stmt = stmt.where(Application.status == "waitlisted")
            elif decision in ("reject", "accept"):
                stmt = stmt.where(
                    Application.status == "decided", latest_decision.c.decision == decision
                )

            stmt = (
                stmt.order_by(Application.ai_total_score.desc().nulls_last())
                .limit(clamped_limit)
                .offset(clamped_offset)
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).all()
            obs.success = True
            return [(row[0], row[1], row[2]) for row in rows]
        except Exception:
            get_logger().warning("db_error", method="list_shortlist_db", exc_info=True)
            obs.success = False
            return []
