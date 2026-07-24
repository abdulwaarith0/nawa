import uuid

import pytest
import pytest_asyncio

from nawa_api.contracts.errors import ApiError
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_application_document_db import create_application_document_db
from nawa_api.db.intake.create_decision_db import create_decision_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.create_scorecard_criterion_db import create_scorecard_criterion_db
from nawa_api.db.intake.create_scorecard_db import create_scorecard_db
from nawa_api.db.intake.update_application_scoring_db import update_application_scoring_db
from nawa_api.db.intake.upsert_dedup_match_db import upsert_dedup_match_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.services.intake.get_scorecard import get_scorecard

_CRITERIA = [{"key": "novelty", "weight": 1.0, "scale_max": 10}]


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _cycle_with_rubric(session, *, version=1, rubric_status="active"):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=session
    )
    rubric = await create_rubric_db(
        program_id=program.id,
        version=version,
        criteria=_CRITERIA,
        name_en="R",
        status=rubric_status,
        session=session,
    )
    return program, cycle, rubric


async def test_missing_application_raises_not_found(bound):
    with pytest.raises(ApiError):
        await get_scorecard(application_id=uuid.uuid4())


async def test_full_detail_shape(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound)
    app = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="Amina",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "great idea"},
        session=bound,
    )
    await update_application_scoring_db(application_id=app.id, total_score=72.0, session=bound)
    scorecard = await create_scorecard_db(
        application_id=app.id,
        rubric_id=rubric.id,
        rubric_version=1,
        prompt_version="v2",
        source="ai",
        total_score=72.0,
        rationale_en="Solid.",
        session=bound,
    )
    await create_scorecard_criterion_db(
        scorecard_id=scorecard.id,
        criterion_key="novelty",
        score=7.2,
        weight=1.0,
        citations=[{"source": "answer:idea", "quote": "great idea"}],
        session=bound,
    )
    await create_application_document_db(
        application_id=app.id,
        storage_key="docs/cv.pdf",
        file_name="cv.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        session=bound,
    )
    reviewer = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"r{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="Reviewer",
        session=bound,
    )
    await create_decision_db(
        application_id=app.id, decided_by=reviewer.id, decision="shortlist", session=bound
    )
    await bound.commit()

    item = await get_scorecard(application_id=app.id)
    assert item["application"]["id"] == str(app.id)
    assert item["application"]["original_answers"] == {"idea": "great idea"}
    assert item["scorecard"]["total_score"] == 72.0
    assert item["scorecard"]["criteria"][0]["citations"] == [
        {"source": "answer:idea", "quote": "great idea"}
    ]
    assert item["scorecard_history"] == []
    assert len(item["documents"]) == 1
    assert item["documents"][0]["file_name"] == "cv.pdf"
    assert item["documents"][0]["url"] is None  # presigning not implemented yet
    assert len(item["decisions"]) == 1
    assert item["decisions"][0]["decision"] == "shortlist"
    assert item["dedup_matches"] == []
    assert item["ai_band"] in {"shortlist", "waitlist", "reject"}


async def test_prior_rubric_version_becomes_history(bound):
    program, cycle, rubric_v1 = await _cycle_with_rubric(bound, version=1, rubric_status="draft")
    rubric_v2 = await create_rubric_db(
        program_id=program.id,
        version=2,
        criteria=_CRITERIA,
        name_en="R2",
        status="active",
        session=bound,
    )
    app = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="Amina",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "great idea"},
        session=bound,
    )
    old_scorecard = await create_scorecard_db(
        application_id=app.id,
        rubric_id=rubric_v1.id,
        rubric_version=1,
        prompt_version="v2",
        source="ai",
        total_score=50.0,
        session=bound,
    )
    new_scorecard = await create_scorecard_db(
        application_id=app.id,
        rubric_id=rubric_v2.id,
        rubric_version=2,
        prompt_version="v2",
        source="ai",
        total_score=80.0,
        session=bound,
    )
    await bound.commit()

    item = await get_scorecard(application_id=app.id)
    assert item["scorecard"]["id"] == str(new_scorecard.id)  # matches the ACTIVE rubric
    assert [h["id"] for h in item["scorecard_history"]] == [str(old_scorecard.id)]


async def test_dedup_matches_surfaced(bound):
    _program, cycle, rubric = await _cycle_with_rubric(bound)
    app_a = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="A",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "x"},
        session=bound,
    )
    app_b = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="B",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "x"},
        session=bound,
    )
    await upsert_dedup_match_db(
        application_id=app_a.id, matched_application_id=app_b.id, similarity=0.9, session=bound
    )
    await bound.commit()

    item = await get_scorecard(application_id=app_a.id)
    assert len(item["dedup_matches"]) == 1
    assert item["dedup_matches"][0]["matched_application_id"] == str(app_b.id)
    assert item["scorecard"] is None  # never scored — no crash on a missing scorecard


async def test_result_is_cached(bound, monkeypatch):
    _program, cycle, rubric = await _cycle_with_rubric(bound)
    app = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="Amina",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "great idea"},
        session=bound,
    )
    await update_application_scoring_db(application_id=app.id, total_score=50.0, session=bound)
    await create_scorecard_db(
        application_id=app.id,
        rubric_id=rubric.id,
        rubric_version=1,
        prompt_version="v2",
        source="ai",
        total_score=50.0,
        session=bound,
    )
    await bound.commit()

    first = await get_scorecard(application_id=app.id)

    import nawa_api.services.intake.get_scorecard as get_scorecard_mod

    async def fail_if_called(**kwargs):
        raise AssertionError("must not touch the db — the cache should have served this")

    monkeypatch.setattr(get_scorecard_mod, "get_application_db", fail_if_called)
    second = await get_scorecard(application_id=app.id)
    assert second == first
