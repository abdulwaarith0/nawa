import uuid

import pytest

from nawa_api.db.membership_requests.create_membership_request_db import (
    create_membership_request_db,
)
from nawa_api.db.membership_requests.get_membership_request_db import get_membership_request_db
from nawa_api.db.membership_requests.list_membership_requests_db import (
    list_membership_requests_db,
)
from nawa_api.db.membership_requests.update_membership_request_status_db import (
    update_membership_request_status_db,
)
from nawa_api.db.users.create_user_db import create_user_db


@pytest.mark.asyncio
async def test_create_membership_request_db_returns_the_created_row(db_session):
    row = await create_membership_request_db(
        full_name="Alice Founder",
        email="alice@example.com",
        organization="Acme",
        reason="I want to join",
        session=db_session,
    )
    assert row is not None
    assert row.email == "alice@example.com"
    assert row.status == "pending"
    assert row.reviewed_by_user_id is None
    assert row.reviewed_at is None


@pytest.mark.asyncio
async def test_create_membership_request_db_defaults_are_optional(db_session):
    row = await create_membership_request_db(
        full_name="Bob Founder", email="bob@example.com", session=db_session
    )
    assert row is not None
    assert row.organization is None
    assert row.reason is None


@pytest.mark.asyncio
async def test_get_membership_request_db_round_trips(db_session):
    created = await create_membership_request_db(
        full_name="Carol Founder", email="carol@example.com", session=db_session
    )
    fetched = await get_membership_request_db(request_id=created.id, session=db_session)
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_membership_request_db_returns_none_for_missing_id(db_session):
    fetched = await get_membership_request_db(request_id=uuid.uuid4(), session=db_session)
    assert fetched is None


@pytest.mark.asyncio
async def test_list_membership_requests_db_orders_most_recent_first(db_session):
    first = await create_membership_request_db(
        full_name="Dave", email="dave@example.com", session=db_session
    )
    await db_session.commit()  # separate transactions so created_at actually differs
    second = await create_membership_request_db(
        full_name="Erin", email="erin@example.com", session=db_session
    )
    rows = await list_membership_requests_db(session=db_session)
    ids = [r.id for r in rows]
    assert ids.index(second.id) < ids.index(first.id)


@pytest.mark.asyncio
async def test_list_membership_requests_db_filters_by_status(db_session):
    pending = await create_membership_request_db(
        full_name="Frank", email="frank@example.com", session=db_session
    )
    approved = await create_membership_request_db(
        full_name="Grace", email="grace@example.com", session=db_session
    )
    await update_membership_request_status_db(
        request_id=approved.id, status="approved", session=db_session
    )

    pending_rows = await list_membership_requests_db(status="pending", session=db_session)
    approved_rows = await list_membership_requests_db(status="approved", session=db_session)

    assert any(r.id == pending.id for r in pending_rows)
    assert not any(r.id == approved.id for r in pending_rows)
    assert any(r.id == approved.id for r in approved_rows)
    assert not any(r.id == pending.id for r in approved_rows)


@pytest.mark.asyncio
async def test_list_membership_requests_db_paginates(db_session):
    for i in range(3):
        await create_membership_request_db(
            full_name=f"User {i}", email=f"page{i}@example.com", session=db_session
        )
    rows = await list_membership_requests_db(limit=2, offset=0, session=db_session)
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_update_membership_request_status_db_sets_reviewer_fields(db_session):
    created = await create_membership_request_db(
        full_name="Henry", email="henry@example.com", session=db_session
    )
    reviewer = await create_user_db(
        email="reviewer@example.com",
        username="reviewer",
        password_hash="hashed",
        full_name="Reviewer",
        session=db_session,
    )
    ok = await update_membership_request_status_db(
        request_id=created.id,
        status="approved",
        reviewed_by_user_id=reviewer.id,
        session=db_session,
    )
    assert ok is True
    fetched = await get_membership_request_db(request_id=created.id, session=db_session)
    assert fetched.status == "approved"
    assert fetched.reviewed_by_user_id == reviewer.id


@pytest.mark.asyncio
async def test_update_membership_request_status_db_returns_false_for_missing_id(db_session):
    ok = await update_membership_request_status_db(
        request_id=uuid.uuid4(), status="rejected", session=db_session
    )
    assert ok is False


@pytest.mark.asyncio
async def test_create_membership_request_db_degrades_to_none_on_db_error(monkeypatch):
    def _broken_session_factory():
        raise RuntimeError("connection lost")

    import nawa_api.db.utils as utils_module

    monkeypatch.setattr(utils_module, "session_factory", _broken_session_factory)
    result = await create_membership_request_db(full_name="X", email="x@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_list_membership_requests_db_degrades_to_empty_list_on_db_error(monkeypatch):
    def _broken_session_factory():
        raise RuntimeError("connection lost")

    import nawa_api.db.utils as utils_module

    monkeypatch.setattr(utils_module, "session_factory", _broken_session_factory)
    result = await list_membership_requests_db()
    assert result == []
