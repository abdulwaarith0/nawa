import uuid

import pytest_asyncio

from nawa_api.ai.evals.against_seed import check_against_seed, format_seed_check
from nawa_api.ai.evals.schemas import GroundTruth
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.create_scorecard_db import create_scorecard_db
from nawa_api.db.intake.update_scorecard_hidden_gem_db import update_scorecard_hidden_gem_db
from nawa_api.db.intake.upsert_dedup_match_db import upsert_dedup_match_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db

_CRITERIA = [{"key": "novelty", "weight": 1.0, "scale_max": 10}]


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


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
    return cycle, rubric


async def _application(session, *, cycle_id):
    return await create_application_db(
        cycle_id=cycle_id,
        applicant_name="A",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "x"},
        session=session,
    )


async def test_no_ground_truth_ids_yields_zero_checked(bound):
    result = await check_against_seed(GroundTruth())
    assert result.hidden_gem_checked == 0
    assert result.dedup_checked == 0
    assert result.hidden_gem_recall_pct == 0.0
    assert result.dedup_recovered_pct == 0.0


async def test_hidden_gem_recall_counts_real_flags(bound):
    cycle, rubric = await _cycle_with_rubric(bound)
    flagged = await _application(bound, cycle_id=cycle.id)
    unflagged = await _application(bound, cycle_id=cycle.id)
    flagged_card = await create_scorecard_db(
        application_id=flagged.id,
        rubric_id=rubric.id,
        rubric_version=1,
        prompt_version="v2",
        source="ai",
        total_score=10.0,
        session=bound,
    )
    await update_scorecard_hidden_gem_db(
        scorecard_id=flagged_card.id,
        hidden_gem=True,
        hidden_gem_reason_ar="س",
        hidden_gem_reason_en="Strong idea.",
        session=bound,
    )
    await create_scorecard_db(
        application_id=unflagged.id,
        rubric_id=rubric.id,
        rubric_version=1,
        prompt_version="v2",
        source="ai",
        total_score=10.0,
        session=bound,
    )
    await bound.commit()

    ground_truth = GroundTruth(hidden_gem_ids=[str(flagged.id), str(unflagged.id)])
    result = await check_against_seed(ground_truth)
    assert result.hidden_gem_checked == 2
    assert result.hidden_gem_recall_pct == 50.0


async def test_hidden_gem_recall_ignores_malformed_ids(bound):
    ground_truth = GroundTruth(hidden_gem_ids=["not-a-uuid"])
    result = await check_against_seed(ground_truth)
    assert result.hidden_gem_checked == 0


async def test_dedup_recovery_counts_planted_pairs(bound):
    cycle, _rubric = await _cycle_with_rubric(bound)
    app_a = await _application(bound, cycle_id=cycle.id)
    app_b = await _application(bound, cycle_id=cycle.id)
    app_c = await _application(bound, cycle_id=cycle.id)
    app_d = await _application(bound, cycle_id=cycle.id)
    await upsert_dedup_match_db(
        application_id=app_a.id, matched_application_id=app_b.id, similarity=0.9, session=bound
    )
    await bound.commit()

    ground_truth = GroundTruth(
        dedup_pair_ids=[[str(app_a.id), str(app_b.id)], [str(app_c.id), str(app_d.id)]]
    )
    result = await check_against_seed(ground_truth)
    assert result.dedup_checked == 2
    assert result.dedup_recovered_pct == 50.0


async def test_dedup_recovery_ignores_malformed_pairs(bound):
    ground_truth = GroundTruth(dedup_pair_ids=[["only-one-id"], ["not-a-uuid", "also-not"]])
    result = await check_against_seed(ground_truth)
    assert result.dedup_checked == 0


def test_format_seed_check_shape():
    from nawa_api.ai.evals.against_seed import SeedCheckResult

    line = format_seed_check(
        SeedCheckResult(
            hidden_gem_recall_pct=50.0,
            hidden_gem_checked=2,
            dedup_recovered_pct=100.0,
            dedup_checked=1,
        )
    )
    assert line == (
        "SEED CHECK: hidden-gem recall 50.0% (2 checked) | "
        "dedup recovered 100.0% (1 checked)"
    )
