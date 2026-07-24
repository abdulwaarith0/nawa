import uuid

import pytest

from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_decision_db import create_decision_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.create_scorecard_db import create_scorecard_db
from nawa_api.db.intake.list_decided_applications_for_export_db import (
    list_decided_applications_for_export_db,
)
from nawa_api.db.intake.update_application_scoring_db import update_application_scoring_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db

_CRITERIA = [{"key": "novelty", "weight": 1.0, "scale_max": 10}]


async def _cycle_with_rubric(session):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=session
    )
    rubric = await create_rubric_db(
        program_id=program.id,
        version=1,
        criteria=_CRITERIA,
        name_en="R",
        status="active",
        session=session,
    )
    return program, cycle, rubric


async def _application(session, *, cycle_id, status, total_score=None):
    app = await create_application_db(
        cycle_id=cycle_id,
        applicant_name="Amina",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "x"},
        session=session,
    )
    if total_score is not None:
        await update_application_scoring_db(
            application_id=app.id, total_score=total_score, session=session
        )
    if status != "scored":
        from sqlalchemy import update

        from nawa_api.models.intake import Application

        await session.execute(
            update(Application).where(Application.id == app.id).values(status=status)
        )
    return app


@pytest.mark.asyncio
async def test_only_decided_applications_are_returned(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    undecided = await _application(
        db_session, cycle_id=cycle.id, status="scored", total_score=50.0
    )
    shortlisted = await _application(
        db_session, cycle_id=cycle.id, status="shortlisted", total_score=90.0
    )

    rows = await list_decided_applications_for_export_db(
        cycle_id=cycle.id, rubric_id=rubric.id, session=db_session
    )
    assert [r[0].id for r in rows] == [shortlisted.id]
    assert undecided.id not in [r[0].id for r in rows]


@pytest.mark.asyncio
async def test_ranked_by_total_score_desc(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    low = await _application(db_session, cycle_id=cycle.id, status="waitlisted", total_score=20.0)
    high = await _application(
        db_session, cycle_id=cycle.id, status="shortlisted", total_score=90.0
    )

    rows = await list_decided_applications_for_export_db(
        cycle_id=cycle.id, rubric_id=rubric.id, session=db_session
    )
    assert [r[0].id for r in rows] == [high.id, low.id]


@pytest.mark.asyncio
async def test_includes_scorecard_and_latest_decision(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    app = await _application(
        db_session, cycle_id=cycle.id, status="decided", total_score=80.0
    )
    await create_scorecard_db(
        application_id=app.id,
        rubric_id=rubric.id,
        rubric_version=1,
        prompt_version="v2",
        source="ai",
        total_score=80.0,
        session=db_session,
    )
    reviewer = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"r{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="Reviewer",
        session=db_session,
    )
    await create_decision_db(
        application_id=app.id,
        decided_by=reviewer.id,
        decision="reject",
        reason="Not a fit.",
        session=db_session,
    )
    await db_session.commit()

    rows = await list_decided_applications_for_export_db(
        cycle_id=cycle.id, rubric_id=rubric.id, session=db_session
    )
    assert len(rows) == 1
    application, scorecard, decision = rows[0]
    assert application.id == app.id
    assert scorecard is not None
    assert scorecard.total_score == 80.0
    assert decision["decision"] == "reject"
    assert decision["reason"] == "Not a fit."
    assert decision["decided_by"] == reviewer.id
    assert decision["created_at"] is not None


@pytest.mark.asyncio
async def test_no_active_rubric_matches_no_scorecard(db_session):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=db_session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=db_session
    )
    app = await _application(
        db_session, cycle_id=cycle.id, status="shortlisted", total_score=50.0
    )

    rows = await list_decided_applications_for_export_db(
        cycle_id=cycle.id, rubric_id=None, session=db_session
    )
    assert len(rows) == 1
    assert rows[0][0].id == app.id
    assert rows[0][1] is None  # no scorecard matched
    assert rows[0][2] is None  # no decision made yet


@pytest.mark.asyncio
async def test_application_with_no_decision_row_has_none_decision(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    app = await _application(
        db_session, cycle_id=cycle.id, status="shortlisted", total_score=60.0
    )

    rows = await list_decided_applications_for_export_db(
        cycle_id=cycle.id, rubric_id=rubric.id, session=db_session
    )
    assert rows[0][0].id == app.id
    assert rows[0][2] is None
