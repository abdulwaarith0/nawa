import uuid

import pytest
import pytest_asyncio

from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.create_scorecard_criterion_db import create_scorecard_criterion_db
from nawa_api.db.intake.create_scorecard_db import create_scorecard_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.scripts.verify_citations import verify

_CRITERIA = [{"key": "novelty", "weight": 1.0, "scale_max": 10}]


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    monkeypatch.setattr("nawa_api.scripts.verify_citations.session_factory", factory)
    return db_session


async def _cycle_and_application(session, *, answers):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=session
    )
    rubric = await create_rubric_db(
        program_id=program.id, version=1, criteria=_CRITERIA, name_en="R", session=session
    )
    app = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="A",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers=answers,
        session=session,
    )
    return rubric, app


@pytest.mark.asyncio
async def test_verify_passes_a_real_verbatim_ai_citation(bound):
    rubric, app = await _cycle_and_application(bound, answers={"idea": "a great water sensor idea"})
    scorecard = await create_scorecard_db(
        application_id=app.id,
        rubric_id=rubric.id,
        rubric_version=1,
        prompt_version="v2",
        source="ai",
        total_score=80.0,
        session=bound,
    )
    await create_scorecard_criterion_db(
        scorecard_id=scorecard.id,
        criterion_key="novelty",
        score=8.0,
        weight=1.0,
        citations=[{"source": "answer:idea", "quote": "a great water sensor idea"}],
        session=bound,
    )
    await bound.commit()

    _total, _failing_count, failing = await verify()
    assert not any(str(app.id) in line for line in failing)


@pytest.mark.asyncio
async def test_verify_flags_a_non_verbatim_ai_citation(bound):
    rubric, app = await _cycle_and_application(bound, answers={"idea": "a great water sensor idea"})
    scorecard = await create_scorecard_db(
        application_id=app.id,
        rubric_id=rubric.id,
        rubric_version=1,
        prompt_version="v2",
        source="ai",
        total_score=80.0,
        session=bound,
    )
    await create_scorecard_criterion_db(
        scorecard_id=scorecard.id,
        criterion_key="novelty",
        score=8.0,
        weight=1.0,
        citations=[{"source": "answer:idea", "quote": "this text does not appear anywhere"}],
        session=bound,
    )
    await bound.commit()

    _total, _failing_count, failing = await verify()
    assert any(str(app.id) in line for line in failing)


@pytest.mark.asyncio
async def test_verify_ignores_non_verbatim_human_scorecards(bound):
    # Mirrors seed_data/applications.py's Season-17 jury scorecards: a human
    # reviewer's shorthand note is not held to the AI verbatim-citation bar.
    rubric, app = await _cycle_and_application(bound, answers={"idea": "a great water sensor idea"})
    scorecard = await create_scorecard_db(
        application_id=app.id,
        rubric_id=rubric.id,
        rubric_version=1,
        prompt_version="seed-v0",
        source="human",
        total_score=80.0,
        session=bound,
    )
    await create_scorecard_criterion_db(
        scorecard_id=scorecard.id,
        criterion_key="novelty",
        score=8.0,
        weight=1.0,
        citations=[{"source": "answer:q1_problem", "quote": "reviewed"}],
        session=bound,
    )
    await bound.commit()

    _total, _failing_count, failing = await verify()
    # Non-verbatim, but source="human" — never scanned, never flagged.
    assert not any(str(app.id) in line for line in failing)
