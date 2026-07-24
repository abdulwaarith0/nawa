import uuid

import pytest

from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_decision_db import create_decision_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.create_scorecard_criterion_db import create_scorecard_criterion_db
from nawa_api.db.intake.create_scorecard_db import create_scorecard_db
from nawa_api.db.intake.list_decisions_for_application_db import (
    list_decisions_for_application_db,
)
from nawa_api.db.intake.list_dedup_matches_db import list_dedup_matches_db
from nawa_api.db.intake.list_pending_dedup_matches_for_applications_db import (
    list_pending_dedup_matches_for_applications_db,
)
from nawa_api.db.intake.list_scorecard_criteria_db import list_scorecard_criteria_db
from nawa_api.db.intake.list_shortlist_db import list_shortlist_db
from nawa_api.db.intake.update_application_scoring_db import update_application_scoring_db
from nawa_api.db.intake.update_scorecard_hidden_gem_db import update_scorecard_hidden_gem_db
from nawa_api.db.intake.upsert_dedup_match_db import upsert_dedup_match_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db

_CRITERIA = [{"key": "novelty", "weight": 1.0, "scale_max": 10}]


async def _cycle_with_rubric(session, *, rubric_status="active"):
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
        status=rubric_status,
        session=session,
    )
    return program, cycle, rubric


async def _scored_application(
    session,
    *,
    cycle_id,
    rubric_id,
    total_score,
    status="scored",
    language="en",
    country=None,
    title=None,
    summary=None,
    email=None,
):
    app = await create_application_db(
        cycle_id=cycle_id,
        applicant_name="Amina",
        applicant_email=email or f"{uuid.uuid4().hex[:8]}@x.io",
        source_language=language,
        original_answers={"idea": "great idea"},
        session=session,
    )
    if country is not None or title is not None:
        from nawa_api.db.intake.update_application_normalization_db import (
            update_application_normalization_db,
        )

        await update_application_normalization_db(
            application_id=app.id,
            source_language=language,
            normalized={"country": country} if country else {},
            title=title,
            summary=summary,
            session=session,
        )
    # update_application_scoring_db always sets status='scored' (the real pipeline
    # never calls it again after a human decision moves status further) — so any
    # later status is applied as a separate override below, not passed at creation.
    await update_application_scoring_db(
        application_id=app.id, total_score=total_score, session=session
    )
    scorecard = await create_scorecard_db(
        application_id=app.id,
        rubric_id=rubric_id,
        rubric_version=1,
        prompt_version="v2",
        source="ai",
        total_score=total_score,
        session=session,
    )
    if status != "scored":
        from sqlalchemy import update

        from nawa_api.models.intake import Application

        await session.execute(
            update(Application).where(Application.id == app.id).values(status=status)
        )
        await session.flush()
    return app, scorecard


@pytest.mark.asyncio
async def test_ranked_by_total_score_desc(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    low, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=20
    )
    high, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=90
    )

    rows = await list_shortlist_db(cycle_id=cycle.id, rubric_id=rubric.id, session=db_session)
    assert [row[0].id for row in rows] == [high.id, low.id]


@pytest.mark.asyncio
async def test_score_band_filter(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    low, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=20
    )
    mid, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=75
    )

    rows = await list_shortlist_db(
        cycle_id=cycle.id, rubric_id=rubric.id, score_min=70, score_max=100, session=db_session
    )
    assert [row[0].id for row in rows] == [mid.id]


@pytest.mark.asyncio
async def test_criterion_min_filter(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    weak, weak_card = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=50
    )
    strong, strong_card = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=50
    )
    await create_scorecard_criterion_db(
        scorecard_id=weak_card.id, criterion_key="novelty", score=3.0, weight=1.0,
        session=db_session,
    )
    await create_scorecard_criterion_db(
        scorecard_id=strong_card.id, criterion_key="novelty", score=9.0, weight=1.0,
        session=db_session,
    )

    rows = await list_shortlist_db(
        cycle_id=cycle.id,
        rubric_id=rubric.id,
        criterion="novelty",
        criterion_min=8.0,
        session=db_session,
    )
    assert [row[0].id for row in rows] == [strong.id]


@pytest.mark.asyncio
async def test_hidden_gem_flag_filter(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    plain, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=20
    )
    gem, gem_card = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10
    )
    await update_scorecard_hidden_gem_db(
        scorecard_id=gem_card.id,
        hidden_gem=True,
        hidden_gem_reason_ar="س",
        hidden_gem_reason_en="Strong idea.",
        session=db_session,
    )

    rows = await list_shortlist_db(
        cycle_id=cycle.id, rubric_id=rubric.id, flags=frozenset({"hidden_gem"}), session=db_session
    )
    assert [row[0].id for row in rows] == [gem.id]


@pytest.mark.asyncio
async def test_normalize_failed_flag_filter(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    _scored, _card = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=50
    )
    failed = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="B",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "x"},
        status="normalize_failed",
        session=db_session,
    )

    rows = await list_shortlist_db(
        cycle_id=cycle.id,
        rubric_id=rubric.id,
        flags=frozenset({"normalize_failed"}),
        session=db_session,
    )
    assert [row[0].id for row in rows] == [failed.id]


@pytest.mark.asyncio
async def test_dedup_pending_flag_filter(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    _plain, _plain_card = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=20
    )
    flagged, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=30
    )
    other, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=40
    )
    await upsert_dedup_match_db(
        application_id=flagged.id,
        matched_application_id=other.id,
        similarity=0.9,
        session=db_session,
    )

    rows = await list_shortlist_db(
        cycle_id=cycle.id,
        rubric_id=rubric.id,
        flags=frozenset({"dedup_pending"}),
        session=db_session,
    )
    assert {row[0].id for row in rows} == {flagged.id, other.id}  # both sides of the pair


@pytest.mark.asyncio
async def test_language_filter(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    _en_app, _en_card = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=20, language="en"
    )
    ar_app, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=30, language="ar"
    )

    rows = await list_shortlist_db(
        cycle_id=cycle.id, rubric_id=rubric.id, language="ar", session=db_session
    )
    assert [row[0].id for row in rows] == [ar_app.id]


@pytest.mark.asyncio
async def test_country_filter(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    qa_app, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=20, country="QA"
    )
    _eg_app, _eg_card = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=30, country="EG"
    )

    rows = await list_shortlist_db(
        cycle_id=cycle.id, rubric_id=rubric.id, country="QA", session=db_session
    )
    assert [row[0].id for row in rows] == [qa_app.id]


@pytest.mark.asyncio
async def test_q_text_search_over_title_and_summary(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    match, _ = await _scored_application(
        db_session,
        cycle_id=cycle.id,
        rubric_id=rubric.id,
        total_score=20,
        title="Water sensor network",
        summary="s",
    )
    _other, _other_card = await _scored_application(
        db_session,
        cycle_id=cycle.id,
        rubric_id=rubric.id,
        total_score=30,
        title="Food delivery app",
        summary="s",
    )

    rows = await list_shortlist_db(
        cycle_id=cycle.id, rubric_id=rubric.id, q="water", session=db_session
    )
    assert [row[0].id for row in rows] == [match.id]


@pytest.mark.asyncio
async def test_decision_filter_states(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    reviewer = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"r{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="Reviewer",
        session=db_session,
    )
    undecided, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10, status="scored"
    )
    shortlisted, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=20, status="shortlisted"
    )
    waitlisted, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=25, status="waitlisted"
    )
    rejected, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=30, status="decided"
    )
    accepted, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=35, status="decided"
    )
    await create_decision_db(
        application_id=rejected.id,
        decided_by=reviewer.id,
        decision="reject",
        session=db_session,
    )
    await create_decision_db(
        application_id=accepted.id,
        decided_by=reviewer.id,
        decision="accept",
        session=db_session,
    )

    undecided_rows = await list_shortlist_db(
        cycle_id=cycle.id, rubric_id=rubric.id, decision="undecided", session=db_session
    )
    assert [r[0].id for r in undecided_rows] == [undecided.id]

    shortlist_rows = await list_shortlist_db(
        cycle_id=cycle.id, rubric_id=rubric.id, decision="shortlist", session=db_session
    )
    assert [r[0].id for r in shortlist_rows] == [shortlisted.id]

    waitlist_rows = await list_shortlist_db(
        cycle_id=cycle.id, rubric_id=rubric.id, decision="waitlist", session=db_session
    )
    assert [r[0].id for r in waitlist_rows] == [waitlisted.id]

    reject_rows = await list_shortlist_db(
        cycle_id=cycle.id, rubric_id=rubric.id, decision="reject", session=db_session
    )
    assert [r[0].id for r in reject_rows] == [rejected.id]
    assert reject_rows[0][2] == "reject"  # latest_decision surfaced in the row

    accept_rows = await list_shortlist_db(
        cycle_id=cycle.id, rubric_id=rubric.id, decision="accept", session=db_session
    )
    assert [r[0].id for r in accept_rows] == [accepted.id]


@pytest.mark.asyncio
async def test_pagination_limit_and_offset(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    apps = []
    for score in (10, 20, 30, 40, 50):
        app, _ = await _scored_application(
            db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=score
        )
        apps.append(app)

    page1 = await list_shortlist_db(
        cycle_id=cycle.id, rubric_id=rubric.id, limit=2, offset=0, session=db_session
    )
    page2 = await list_shortlist_db(
        cycle_id=cycle.id, rubric_id=rubric.id, limit=2, offset=2, session=db_session
    )
    assert [r[0].ai_total_score for r in page1] == [50, 40]
    assert [r[0].ai_total_score for r in page2] == [30, 20]


@pytest.mark.asyncio
async def test_list_scorecard_criteria_db_batches_multiple_scorecards(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    _app_a, card_a = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10
    )
    _app_b, card_b = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=20
    )
    await create_scorecard_criterion_db(
        scorecard_id=card_a.id, criterion_key="novelty", score=5.0, weight=1.0, session=db_session
    )
    await create_scorecard_criterion_db(
        scorecard_id=card_b.id, criterion_key="novelty", score=7.0, weight=1.0, session=db_session
    )

    rows = await list_scorecard_criteria_db(
        scorecard_ids=[card_a.id, card_b.id], session=db_session
    )
    assert {r.scorecard_id for r in rows} == {card_a.id, card_b.id}
    assert await list_scorecard_criteria_db(scorecard_ids=[], session=db_session) == []


@pytest.mark.asyncio
async def test_list_dedup_matches_db_finds_both_directions(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    app_a, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10
    )
    app_b, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=20
    )
    await upsert_dedup_match_db(
        application_id=app_a.id,
        matched_application_id=app_b.id,
        similarity=0.9,
        session=db_session,
    )

    from_a = await list_dedup_matches_db(application_id=app_a.id, session=db_session)
    from_b = await list_dedup_matches_db(application_id=app_b.id, session=db_session)
    assert len(from_a) == 1
    assert len(from_b) == 1  # found even though app_b is the matched_ side, not application_ side


@pytest.mark.asyncio
async def test_list_pending_dedup_matches_for_applications_db(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    app_a, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10
    )
    app_b, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=20
    )
    unrelated, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=30
    )
    await upsert_dedup_match_db(
        application_id=app_a.id,
        matched_application_id=app_b.id,
        similarity=0.9,
        session=db_session,
    )

    assert await list_pending_dedup_matches_for_applications_db(
        application_ids=[], session=db_session
    ) == []
    rows = await list_pending_dedup_matches_for_applications_db(
        application_ids=[app_a.id, app_b.id, unrelated.id], session=db_session
    )
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_list_decisions_for_application_db_newest_first(db_session):
    _program, cycle, rubric = await _cycle_with_rubric(db_session)
    app, _ = await _scored_application(
        db_session, cycle_id=cycle.id, rubric_id=rubric.id, total_score=10, status="decided"
    )
    reviewer = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"r{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="Reviewer",
        session=db_session,
    )
    # Postgres's now() returns the TRANSACTION's start time, not wall-clock time
    # per statement — commit between writes so created_at genuinely differs and
    # the "newest first" ordering is actually exercised, not coincidental.
    await create_decision_db(
        application_id=app.id, decided_by=reviewer.id, decision="waitlist", session=db_session
    )
    await db_session.commit()
    await create_decision_db(
        application_id=app.id, decided_by=reviewer.id, decision="reject", session=db_session
    )
    await db_session.commit()

    rows = await list_decisions_for_application_db(application_id=app.id, session=db_session)
    assert len(rows) == 2
    assert rows[0].decision == "reject"  # most recent write, listed first
