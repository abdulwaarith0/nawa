import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from nawa_api.contracts.errors import ERR_INVALID_FIELDS, ERR_NOT_FOUND, ApiError
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.upsert_dedup_match_db import upsert_dedup_match_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.models.intake import DedupMatch
from nawa_api.services.intake.resolve_dedup_match import resolve_dedup_match
from nawa_api.utils.password import hash_password


async def _user(session):
    email = f"{uuid.uuid4().hex[:8]}@x.io"
    return await create_user_db(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("password123"),
        full_name="Reviewer",
        session=session,
    )


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _pair(session):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="competition", name_en="P", session=session
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C", session=session
    )
    a = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="A",
        applicant_email="a@x.io",
        source_language="en",
        original_answers={},
        session=session,
    )
    b = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="B",
        applicant_email="b@x.io",
        source_language="en",
        original_answers={},
        session=session,
    )
    await upsert_dedup_match_db(
        application_id=a.id, matched_application_id=b.id, similarity=0.91, session=session
    )
    row = (
        await session.execute(
            select(DedupMatch).where(DedupMatch.application_id == a.id)
        )
    ).scalar_one()
    return row


@pytest.mark.asyncio
async def test_resolve_dedup_match_confirms_and_stamps_reviewer(bound):
    match = await _pair(bound)
    reviewer = await _user(bound)
    await bound.commit()

    result = await resolve_dedup_match(
        match_id=match.id, status="confirmed", reviewed_by=reviewer.id
    )

    assert result == {
        "id": str(match.id),
        "status": "confirmed",
        "reviewed_by": str(reviewer.id),
    }
    await bound.refresh(match)
    assert match.status == "confirmed"
    assert match.reviewed_by == reviewer.id
    assert match.reviewed_at is not None


@pytest.mark.asyncio
async def test_resolve_dedup_match_dismisses(bound):
    match = await _pair(bound)
    reviewer = await _user(bound)
    await bound.commit()
    result = await resolve_dedup_match(
        match_id=match.id, status="dismissed", reviewed_by=reviewer.id
    )
    assert result["status"] == "dismissed"


@pytest.mark.asyncio
async def test_resolve_dedup_match_invalid_status_raises_invalid_fields(bound):
    match = await _pair(bound)
    await bound.commit()
    with pytest.raises(ApiError) as exc_info:
        await resolve_dedup_match(match_id=match.id, status="approved", reviewed_by=uuid.uuid4())
    assert exc_info.value == ERR_INVALID_FIELDS


@pytest.mark.asyncio
async def test_resolve_dedup_match_missing_match_raises_not_found(bound):
    with pytest.raises(ApiError) as exc_info:
        await resolve_dedup_match(
            match_id=uuid.uuid4(), status="confirmed", reviewed_by=uuid.uuid4()
        )
    assert exc_info.value == ERR_NOT_FOUND
