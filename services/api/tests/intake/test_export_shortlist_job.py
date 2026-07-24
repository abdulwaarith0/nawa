import uuid
from io import BytesIO

import openpyxl
import pytest
import pytest_asyncio

from nawa_api.contracts.errors import ApiError
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_decision_db import create_decision_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.create_scorecard_criterion_db import create_scorecard_criterion_db
from nawa_api.db.intake.create_scorecard_db import create_scorecard_db
from nawa_api.db.intake.update_application_scoring_db import update_application_scoring_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.jobs.export_shortlist import export_shortlist
from nawa_api.models.intake import Application
from nawa_api.runtime.storage import get_storage_provider, reset_storage_provider_cache

_CRITERIA = [{"key": "novelty", "weight": 1.0, "scale_max": 10}]


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    reset_storage_provider_cache()
    yield db_session
    reset_storage_provider_cache()


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


async def _decided_application(session, *, cycle_id, rubric_id, status, total_score, title):
    from sqlalchemy import update

    app = await create_application_db(
        cycle_id=cycle_id,
        applicant_name="Amina Al-Sayed",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "great idea"},
        session=session,
    )
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
    await create_scorecard_criterion_db(
        scorecard_id=scorecard.id,
        criterion_key="novelty",
        score=8.0,
        weight=1.0,
        session=session,
    )
    await session.execute(
        update(Application).where(Application.id == app.id).values(status=status, title=title)
    )
    return app


def _load_sheet(data: bytes):
    workbook = openpyxl.load_workbook(BytesIO(data))
    sheet = workbook.active
    return [tuple(row) for row in sheet.iter_rows(values_only=True)]


async def test_missing_cycle_raises_not_found(bound):
    with pytest.raises(ApiError):
        await export_shortlist(cycle_id=str(uuid.uuid4()))


async def test_no_decided_applications_produces_header_only_workbook(bound):
    cycle, _rubric = await _cycle_with_rubric(bound)
    await bound.commit()

    result = await export_shortlist(cycle_id=str(cycle.id))
    assert result["row_count"] == 0

    data = get_storage_provider().get_object(result["storage_key"])
    rows = _load_sheet(data)
    assert len(rows) == 1  # header row only
    assert "Rank" in rows[0]


async def test_row_count_matches_decided_applications(bound):
    cycle, rubric = await _cycle_with_rubric(bound)
    await _decided_application(
        bound, cycle_id=cycle.id, rubric_id=rubric.id, status="shortlisted",
        total_score=90.0, title="Water sensors",
    )
    await _decided_application(
        bound, cycle_id=cycle.id, rubric_id=rubric.id, status="waitlisted",
        total_score=50.0, title="Food app",
    )
    # An undecided (merely scored) application must NOT be counted.
    await _decided_application(
        bound, cycle_id=cycle.id, rubric_id=rubric.id, status="scored",
        total_score=70.0, title="Undecided idea",
    )
    await bound.commit()

    result = await export_shortlist(cycle_id=str(cycle.id))
    assert result["row_count"] == 2


async def test_exports_criteria_columns_and_decision_info(bound):
    cycle, rubric = await _cycle_with_rubric(bound)
    app = await _decided_application(
        bound, cycle_id=cycle.id, rubric_id=rubric.id, status="decided",
        total_score=42.0, title="Water sensors",
    )
    reviewer = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"r{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="Reviewer One",
        session=bound,
    )
    await create_decision_db(
        application_id=app.id,
        decided_by=reviewer.id,
        decision="reject",
        reason="Not a fit for this cycle.",
        session=bound,
    )
    await bound.commit()

    result = await export_shortlist(cycle_id=str(cycle.id))
    assert result["row_count"] == 1

    data = get_storage_provider().get_object(result["storage_key"])
    rows = _load_sheet(data)
    header, data_row = rows[0], rows[1]
    assert "novelty" in header
    novelty_index = header.index("novelty")
    assert data_row[novelty_index] == 8.0
    assert data_row[header.index("Decision")] == "reject"
    assert data_row[header.index("Decision Reason")] == "Not a fit for this cycle."
    assert data_row[header.index("Decider")] == "Reviewer One"
    assert data_row[header.index("Applicant")] == "Amina Al-Sayed"
    assert data_row[header.index("Title")] == "Water sensors"
    assert data_row[header.index("Total Score")] == 42.0
    assert data_row[header.index("Rank")] == 1


async def test_returns_a_presigned_url(bound):
    cycle, _rubric = await _cycle_with_rubric(bound)
    await bound.commit()

    result = await export_shortlist(cycle_id=str(cycle.id))
    assert result["url"] is not None
    assert result["storage_key"].startswith(f"intake/exports/{cycle.id}/")
    assert result["storage_key"].endswith(".xlsx")
