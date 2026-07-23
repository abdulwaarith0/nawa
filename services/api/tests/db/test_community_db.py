from datetime import UTC, datetime, timedelta

import pytest

from nawa_api.db.community.create_mentorship_db import create_mentorship_db
from nawa_api.db.community.create_opportunity_db import create_opportunity_db
from nawa_api.db.community.create_opportunity_match_db import create_opportunity_match_db
from nawa_api.db.community.create_request_db import create_request_db
from nawa_api.db.community.create_request_match_db import create_request_match_db
from nawa_api.db.community.list_opportunities_db import list_opportunities_db
from nawa_api.db.community.list_requests_db import list_requests_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.users.create_user_db import create_user_db


async def _make_profile(db_session, *, email: str, handle: str):
    user = await create_user_db(
        email=email,
        username=handle,
        password_hash="hashed",
        full_name=handle,
        session=db_session,
    )
    return await create_founder_profile_db(
        user_id=user.id, handle=handle, display_name_en=handle, session=db_session
    )


@pytest.mark.asyncio
async def test_request_lifecycle_and_matching(db_session):
    profile = await _make_profile(db_session, email="req@example.com", handle="req-founder")
    request = await create_request_db(
        profile_id=profile.id,
        kind="talent",
        title_en="Need a mechanical engineer",
        skills_needed=["mechanical-engineering"],
        status="open",
        session=db_session,
    )
    assert request is not None

    helper = await _make_profile(db_session, email="helper@example.com", handle="helper-founder")
    match = await create_request_match_db(
        request_id=request.id,
        profile_id=helper.id,
        score=0.87,
        rationale_en="Skills: mechanical engineering",
        matched_skills=["mechanical-engineering"],
        session=db_session,
    )
    assert match is not None

    rows = await list_requests_db(status="open", session=db_session)
    assert any(r.id == request.id for r in rows)


@pytest.mark.asyncio
async def test_opportunity_lifecycle_and_closing_soon_sort(db_session):
    staff = await create_user_db(
        email="staff@example.com",
        username="staff1",
        password_hash="hashed",
        full_name="Staff",
        session=db_session,
    )
    near = await create_opportunity_db(
        posted_by_user_id=staff.id,
        kind="internship",
        title_en="Closing soon",
        deadline_at=datetime.now(UTC) + timedelta(days=2),
        status="open",
        session=db_session,
    )
    far = await create_opportunity_db(
        posted_by_user_id=staff.id,
        kind="internship",
        title_en="Closing later",
        deadline_at=datetime.now(UTC) + timedelta(days=30),
        status="open",
        session=db_session,
    )
    rows = await list_opportunities_db(status="open", session=db_session)
    ids = [o.id for o in rows]
    assert ids.index(near.id) < ids.index(far.id)

    candidate = await _make_profile(db_session, email="cand@example.com", handle="cand-founder")
    om = await create_opportunity_match_db(
        opportunity_id=near.id, profile_id=candidate.id, score=0.7, session=db_session
    )
    assert om is not None


@pytest.mark.asyncio
async def test_mentorship_creation(db_session):
    mentor = await _make_profile(db_session, email="mentor@example.com", handle="mentor-1")
    mentee = await _make_profile(db_session, email="mentee@example.com", handle="mentee-1")
    mentorship = await create_mentorship_db(
        mentor_profile_id=mentor.id,
        mentee_profile_id=mentee.id,
        matched_by="ai",
        score=0.75,
        rationale_en="Shared sector experience.",
        session=db_session,
    )
    assert mentorship is not None
    assert mentorship.status == "suggested"
