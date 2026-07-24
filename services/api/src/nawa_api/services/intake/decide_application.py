"""Human decisions — the only path that decides anything (06-intake-copilot.md
§6.2). Computes the AI recommendation band from the application's own rank in
its cycle; a human decision that diverges from that band requires a reason.
On `accept`, links a founder profile (creating a user + profile if the
applicant has neither yet) and creates cohort membership, all in the SAME
transaction as the `decisions` row — never a decision with no application
status change, never a cohort acceptance with no decision on record.

Cross-domain cache invalidation on `accept` (profiles/community globs) is
fired even though neither domain's services exist in this codebase yet
(slices 07/08) — the SCAN-based glob helper is a no-op against keys that
were never written, so this is safe, forward-compatible plumbing per spec.
"""

from __future__ import annotations

import secrets
import uuid

from nawa_api.contracts.errors import ERR_INTERNAL, ERR_INVALID_FIELDS, ERR_NOT_FOUND
from nawa_api.db.cohorts.get_cohort_db import get_cohort_db
from nawa_api.db.cohorts.upsert_cohort_member_db import upsert_cohort_member_db
from nawa_api.db.intake.count_higher_scoring_applications_db import (
    count_higher_scoring_applications_db,
)
from nawa_api.db.intake.create_decision_db import create_decision_db
from nawa_api.db.intake.get_active_rubric_db import get_active_rubric_db
from nawa_api.db.intake.get_application_db import get_application_db
from nawa_api.db.intake.list_scorecards_for_application_db import (
    list_scorecards_for_application_db,
)
from nawa_api.db.intake.update_application_decision_status_db import (
    update_application_decision_status_db,
)
from nawa_api.db.intake.update_application_profile_link_db import (
    update_application_profile_link_db,
)
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.profiles.get_founder_profile_by_user_id_db import (
    get_founder_profile_by_user_id_db,
)
from nawa_api.db.programs.get_program_cycle_db import get_program_cycle_db
from nawa_api.db.programs.get_program_db import get_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.db.users.get_user_by_email_db import get_user_by_email_db
from nawa_api.db.utils import in_transaction
from nawa_api.services.intake.compute_ai_band import compute_ai_band, resolve_capacities
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys
from nawa_api.utils.password import hash_password

_DECISION_STATUS = {
    "shortlist": "shortlisted",
    "waitlist": "waitlisted",
    "reject": "decided",
    "accept": "decided",
}
_DECIDABLE_STATUSES = frozenset({"scored", "shortlisted", "waitlisted", "decided"})


class _TransactionFailed(Exception):
    """Raised only INSIDE `async with in_transaction()` to trigger a
    rollback, then caught immediately outside it and translated to
    ERR_INTERNAL. `ApiError` is a frozen dataclass; raising one through
    `in_transaction()`'s nested generator-based context managers (its own
    `@asynccontextmanager` wrapping `session.begin()`) trips a Python 3.12
    `FrozenInstanceError` when the generator machinery tries to reset
    `__traceback__` on the same frozen instance at each layer it propagates
    through. A plain, non-frozen exception has no such problem."""


async def _compute_current_ai_band(application) -> tuple[str, int | None]:
    """Returns (ai_band, rubric_version of the application's current AI
    scorecard, or None if it has none)."""
    cycle = await get_program_cycle_db(cycle_id=application.cycle_id)
    rubric_version = None
    if cycle is None:
        shortlist_cap, waitlist_cap = resolve_capacities(program_config={}, cycle_config={})
    else:
        program = await get_program_db(program_id=cycle.program_id)
        active_rubric = await get_active_rubric_db(program_id=cycle.program_id)
        if active_rubric is not None:
            scorecards = await list_scorecards_for_application_db(application_id=application.id)
            current = next(
                (
                    sc
                    for sc in scorecards
                    if sc.source == "ai" and sc.rubric_id == active_rubric.id
                ),
                None,
            )
            rubric_version = current.rubric_version if current else None
        shortlist_cap, waitlist_cap = resolve_capacities(
            program_config=program.config if program is not None else {},
            cycle_config=cycle.config,
        )

    higher = await count_higher_scoring_applications_db(
        cycle_id=application.cycle_id, total_score=application.ai_total_score or 0.0
    )
    band = compute_ai_band(
        rank=higher + 1, shortlist_capacity=shortlist_cap, waitlist_capacity=waitlist_cap
    )
    return band, rubric_version


async def _ensure_founder_profile(application, *, session) -> uuid.UUID:
    """Raises `_TransactionFailed` (never `ApiError`) on any write failure —
    see that class's docstring for why."""
    if application.profile_id is not None:
        return application.profile_id

    user = await get_user_by_email_db(email=application.applicant_email, session=session)
    if user is None:
        local_part = application.applicant_email.split("@")[0]
        # Random, unusable password — the applicant sets their own via the
        # existing forgot/reset-password flow; no new invite mechanism needed.
        user = await create_user_db(
            email=application.applicant_email,
            username=f"{local_part}-{uuid.uuid4().hex[:8]}",
            password_hash=hash_password(secrets.token_urlsafe(32)),
            full_name=application.applicant_name,
            session=session,
        )
        if user is None:
            raise _TransactionFailed

    profile = await get_founder_profile_by_user_id_db(user_id=user.id, session=session)
    if profile is None:
        local_part = application.applicant_email.split("@")[0]
        profile = await create_founder_profile_db(
            user_id=user.id,
            handle=f"{local_part}-{uuid.uuid4().hex[:8]}",
            display_name_en=application.applicant_name,
            venture_name_en=application.title,
            venture_summary_en=application.summary,
            country=application.normalized.get("country"),
            session=session,
        )
        if profile is None:
            raise _TransactionFailed

    ok = await update_application_profile_link_db(
        application_id=application.id, profile_id=profile.id, session=session
    )
    if not ok:
        raise _TransactionFailed
    return profile.id


async def decide_application(
    *,
    application_id: uuid.UUID,
    decision: str,
    reason: str | None,
    cohort_id: uuid.UUID | None,
    decided_by: uuid.UUID,
) -> dict:
    if decision not in _DECISION_STATUS:
        raise ERR_INVALID_FIELDS

    application = await get_application_db(application_id=application_id)
    if application is None:
        raise ERR_NOT_FOUND
    if application.status not in _DECIDABLE_STATUSES:
        raise ERR_INVALID_FIELDS

    if decision == "accept":
        if cohort_id is None:
            raise ERR_INVALID_FIELDS
        cohort = await get_cohort_db(cohort_id=cohort_id)
        if cohort is None or cohort.cycle_id != application.cycle_id:
            raise ERR_INVALID_FIELDS
    elif cohort_id is not None:
        raise ERR_INVALID_FIELDS

    ai_band, rubric_version = await _compute_current_ai_band(application)
    # `ai_band` only ever names shortlist/waitlist/reject — it has no notion of
    # "accept" (that's a human-only, cohort-admitting action layered on top of
    # a shortlist recommendation). Accepting someone the AI would have
    # shortlisted is following the recommendation, not overriding it; accepting
    # past a waitlist/reject band is the actual divergence that needs a reason.
    matches_band = decision == ai_band or (decision == "accept" and ai_band == "shortlist")
    overridden = not matches_band
    if overridden and not reason:
        raise ERR_INVALID_FIELDS

    new_status = _DECISION_STATUS[decision]
    previous_value = {
        "status": application.status,
        "ai_total_score": application.ai_total_score,
        "ai_band": ai_band,
        "rubric_version": rubric_version,
    }
    new_value = {"status": new_status}

    profile_id: uuid.UUID | None = None
    decision_id: uuid.UUID | None = None
    try:
        async with in_transaction() as session:
            row = await create_decision_db(
                application_id=application_id,
                decided_by=decided_by,
                decision=decision,
                previous_value=previous_value,
                new_value=new_value,
                reason=reason,
                session=session,
            )
            if row is None:
                raise _TransactionFailed
            decision_id = row.id
            status_ok = await update_application_decision_status_db(
                application_id=application_id, status=new_status, session=session
            )
            if not status_ok:
                raise _TransactionFailed
            if decision == "accept":
                profile_id = await _ensure_founder_profile(application, session=session)
                await upsert_cohort_member_db(
                    cohort_id=cohort_id, profile_id=profile_id, session=session
                )
    except _TransactionFailed:
        raise ERR_INTERNAL from None

    await invalidate_cache_keys(
        "services:intake:list_shortlist:*", f"services:intake:get_scorecard:{application_id}"
    )
    if decision == "accept":
        await invalidate_cache_keys(
            "services:profiles:get_founder_profile:*",
            "services:profiles:list_profile_program_history:*",
            "services:community:list_directory:*",
        )

    return {
        "decision_id": str(decision_id),
        "application_id": str(application_id),
        "status": new_status,
        "decision": decision,
        "ai_band": ai_band,
        "overridden": overridden,
        "profile_id": str(profile_id) if profile_id else None,
    }
