import uuid

import pytest
from sqlalchemy import select

from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_application_document_db import create_application_document_db
from nawa_api.db.intake.create_application_embedding_db import create_application_embedding_db
from nawa_api.db.intake.create_application_upload_db import create_application_upload_db
from nawa_api.db.intake.create_decision_db import create_decision_db
from nawa_api.db.intake.create_dedup_match_db import create_dedup_match_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.create_scorecard_criterion_db import create_scorecard_criterion_db
from nawa_api.db.intake.create_scorecard_db import create_scorecard_db
from nawa_api.db.intake.get_active_rubric_db import get_active_rubric_db
from nawa_api.db.intake.get_application_db import get_application_db
from nawa_api.db.intake.get_application_embedding_db import get_application_embedding_db
from nawa_api.db.intake.list_application_documents_db import list_application_documents_db
from nawa_api.db.intake.list_applications_by_email_db import list_applications_by_email_db
from nawa_api.db.intake.list_applications_db import list_applications_db
from nawa_api.db.intake.list_scorecards_for_application_db import (
    list_scorecards_for_application_db,
)
from nawa_api.db.intake.list_similar_applications_db import list_similar_applications_db
from nawa_api.db.intake.update_application_scoring_db import update_application_scoring_db
from nawa_api.db.intake.upsert_dedup_match_db import upsert_dedup_match_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.models.intake import DedupMatch
from nawa_api.runtime.settings import get_settings

_DIM = get_settings().embeddings_dimension


def _vec(seed: float) -> list[float]:
    v = [0.0] * _DIM
    v[0] = seed
    v[1] = 1.0
    return v


@pytest.mark.asyncio
async def test_rubric_create_and_get_active(db_session):
    program = await create_program_db(
        slug="sos-rubric-test", kind="competition", name_en="SoS", session=db_session
    )
    created = await create_rubric_db(
        program_id=program.id,
        version=1,
        criteria=[{"key": "novelty", "weight": 1.0, "scale_max": 10}],
        name_en="SoS Rubric v1",
        status="active",
        session=db_session,
    )
    assert created is not None
    fetched = await get_active_rubric_db(program_id=program.id, session=db_session)
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_application_lifecycle(db_session):
    program = await create_program_db(
        slug="sos-app-test", kind="competition", name_en="SoS", session=db_session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug="s18", name_en="Season 18", session=db_session
    )
    uploader = await create_user_db(
        email="uploader@example.com",
        username="uploader",
        password_hash="hashed",
        full_name="Uploader",
        session=db_session,
    )
    upload = await create_application_upload_db(
        cycle_id=cycle.id,
        storage_key="uploads/batch1.xlsx",
        file_name="batch1.xlsx",
        mime_type="application/vnd.ms-excel",
        size_bytes=1024,
        uploaded_by_user_id=uploader.id,
        session=db_session,
    )
    assert upload is not None

    application = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="Fatima Al-Sayed",
        applicant_email="fatima@example.com",
        source_language="ar",
        original_answers={"q1": "نص عربي حقيقي عن فكرة مبتكرة"},
        source_upload_id=upload.id,
        session=db_session,
    )
    assert application is not None
    assert application.status == "submitted"

    fetched = await get_application_db(application_id=application.id, session=db_session)
    assert fetched is not None

    doc = await create_application_document_db(
        application_id=application.id,
        storage_key="docs/cv.pdf",
        file_name="cv.pdf",
        mime_type="application/pdf",
        size_bytes=2048,
        kind="cv",
        extracted_text="Real CV text.",
        session=db_session,
    )
    assert doc is not None

    docs = await list_application_documents_db(application_id=application.id, session=db_session)
    assert [d.id for d in docs] == [doc.id]

    rows = await list_applications_db(cycle_id=cycle.id, session=db_session)
    assert any(a.id == application.id for a in rows)


@pytest.mark.asyncio
async def test_scorecard_and_criteria_and_decision(db_session):
    program = await create_program_db(
        slug="sos-score-test", kind="competition", name_en="SoS", session=db_session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug="s18b", name_en="Season 18b", session=db_session
    )
    rubric = await create_rubric_db(
        program_id=program.id,
        version=1,
        criteria=[{"key": "novelty", "weight": 1.0}],
        name_en="Rubric",
        status="active",
        session=db_session,
    )
    application = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="Test Applicant",
        applicant_email="applicant@example.com",
        source_language="en",
        original_answers={"q1": "answer"},
        session=db_session,
    )
    scorecard = await create_scorecard_db(
        application_id=application.id,
        rubric_id=rubric.id,
        rubric_version=1,
        prompt_version="v1",
        source="ai",
        total_score=85.5,
        rationale_en="Strong novelty.",
        session=db_session,
    )
    assert scorecard is not None
    criterion = await create_scorecard_criterion_db(
        scorecard_id=scorecard.id,
        criterion_key="novelty",
        score=9.0,
        weight=1.0,
        rationale_en="Cites application §1.",
        citations=[{"source": "answer:q1", "quote": "answer"}],
        session=db_session,
    )
    assert criterion is not None

    scorecards = await list_scorecards_for_application_db(
        application_id=application.id, session=db_session
    )
    assert any(sc.id == scorecard.id for sc in scorecards)

    reviewer = await create_user_db(
        email="reviewer1@example.com",
        username="reviewer1",
        password_hash="hashed",
        full_name="Reviewer One",
        session=db_session,
    )
    decision = await create_decision_db(
        application_id=application.id,
        decided_by=reviewer.id,
        decision="shortlist",
        previous_value={"status": "scored"},
        new_value={"status": "shortlisted"},
        session=db_session,
    )
    assert decision is not None

    updated = await update_application_scoring_db(
        application_id=application.id, total_score=72.5, session=db_session
    )
    assert updated is True
    rescored = await get_application_db(application_id=application.id, session=db_session)
    assert rescored.status == "scored"
    assert rescored.ai_total_score == 72.5
    assert rescored.scored_at is not None


@pytest.mark.asyncio
async def test_dedup_match_and_similarity_knn(db_session):
    program = await create_program_db(
        slug="sos-dedup-test", kind="competition", name_en="SoS", session=db_session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug="s18c", name_en="Season 18c", session=db_session
    )
    app_a = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="A",
        applicant_email="a@example.com",
        source_language="en",
        original_answers={"q1": "idea"},
        session=db_session,
    )
    app_b = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="B",
        applicant_email="b@example.com",
        source_language="en",
        original_answers={"q1": "similar idea"},
        session=db_session,
    )
    app_c = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="C",
        applicant_email="c@example.com",
        source_language="en",
        original_answers={"q1": "unrelated"},
        session=db_session,
    )

    await create_application_embedding_db(
        application_id=app_a.id,
        embedding=_vec(1.0),
        embedding_model="mock",
        source_hash="h1",
        session=db_session,
    )
    await create_application_embedding_db(
        application_id=app_b.id,
        embedding=_vec(1.01),
        embedding_model="mock",
        source_hash="h2",
        session=db_session,
    )
    await create_application_embedding_db(
        application_id=app_c.id,
        embedding=[0.0, -1.0] + [0.0] * (len(_vec(1.0)) - 2),
        embedding_model="mock",
        source_hash="h3",
        session=db_session,
    )

    neighbors = await list_similar_applications_db(application_id=app_a.id, k=2, session=db_session)
    assert len(neighbors) == 2
    assert neighbors[0][0] == app_b.id  # closest neighbor is the near-duplicate
    assert neighbors[0][1] > 0.9

    match = await create_dedup_match_db(
        application_id=app_a.id,
        matched_application_id=app_b.id,
        similarity=neighbors[0][1],
        session=db_session,
    )
    assert match is not None
    assert match.status == "pending"


@pytest.mark.asyncio
async def test_get_active_rubric_db_returns_none_when_no_active_rubric(db_session):
    program = await create_program_db(
        slug="no-rubric-test", kind="competition", name_en="No Rubric", session=db_session
    )
    result = await get_active_rubric_db(program_id=program.id, session=db_session)
    assert result is None


@pytest.mark.asyncio
async def test_list_similar_applications_db_returns_empty_for_unembedded_application(db_session):
    result = await list_similar_applications_db(application_id=uuid.uuid4(), session=db_session)
    assert result == []


@pytest.mark.asyncio
async def test_get_application_embedding_db_round_trips(db_session):
    program = await create_program_db(
        slug=f"emb-get-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=db_session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug="c1", name_en="C", session=db_session
    )
    app = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="A",
        applicant_email=f"{uuid.uuid4().hex[:8]}@example.com",
        source_language="en",
        original_answers={"q1": "idea"},
        session=db_session,
    )
    assert await get_application_embedding_db(application_id=app.id, session=db_session) is None

    await create_application_embedding_db(
        application_id=app.id,
        embedding=_vec(2.0),
        embedding_model="mock",
        source_hash="hx",
        session=db_session,
    )
    row = await get_application_embedding_db(application_id=app.id, session=db_session)
    assert row is not None
    assert row.embedding_model == "mock"
    assert row.source_hash == "hx"


@pytest.mark.asyncio
async def test_upsert_dedup_match_db_converges_on_conflict(db_session):
    program = await create_program_db(
        slug=f"dedup-upsert-{uuid.uuid4().hex[:8]}",
        kind="competition",
        name_en="P",
        session=db_session,
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug="c1", name_en="C", session=db_session
    )
    app_a = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="A",
        applicant_email=f"{uuid.uuid4().hex[:8]}@example.com",
        source_language="en",
        original_answers={"q1": "idea"},
        session=db_session,
    )
    app_b = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="B",
        applicant_email=f"{uuid.uuid4().hex[:8]}@example.com",
        source_language="en",
        original_answers={"q1": "idea"},
        session=db_session,
    )

    ok1 = await upsert_dedup_match_db(
        application_id=app_a.id,
        matched_application_id=app_b.id,
        similarity=0.85,
        session=db_session,
    )
    assert ok1 is True

    ok2 = await upsert_dedup_match_db(
        application_id=app_a.id,
        matched_application_id=app_b.id,
        similarity=0.91,  # a re-scan refreshing the score
        session=db_session,
    )
    assert ok2 is True

    stmt = select(DedupMatch).where(DedupMatch.application_id == app_a.id)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1  # upsert converged, no duplicate row
    assert rows[0].similarity == 0.91


@pytest.mark.asyncio
async def test_list_applications_by_email_db_finds_matches_across_cycles(db_session):
    program = await create_program_db(
        slug=f"email-dedup-{uuid.uuid4().hex[:8]}",
        kind="competition",
        name_en="P",
        session=db_session,
    )
    cycle_17 = await create_program_cycle_db(
        program_id=program.id, slug="s17", name_en="S17", session=db_session
    )
    cycle_18 = await create_program_cycle_db(
        program_id=program.id, slug="s18", name_en="S18", session=db_session
    )
    shared_email = f"{uuid.uuid4().hex[:8]}@resubmitter.io"
    app_17 = await create_application_db(
        cycle_id=cycle_17.id,
        applicant_name="A",
        applicant_email=shared_email,
        source_language="en",
        original_answers={"q1": "idea"},
        session=db_session,
    )
    app_18 = await create_application_db(
        cycle_id=cycle_18.id,
        applicant_name="A",
        applicant_email=shared_email,
        source_language="en",
        original_answers={"q1": "idea, resubmitted"},
        session=db_session,
    )

    rows = await list_applications_by_email_db(applicant_email=shared_email, session=db_session)
    assert {r.id for r in rows} == {app_17.id, app_18.id}
