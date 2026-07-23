import uuid

import pytest

from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.db.users.get_user_by_email_db import get_user_by_email_db
from nawa_api.db.users.get_user_by_id_db import get_user_by_id_db
from nawa_api.db.users.get_user_by_identifier_db import get_user_by_identifier_db
from nawa_api.db.users.list_users_db import list_users_db
from nawa_api.db.users.update_user_db import update_user_db


@pytest.mark.asyncio
async def test_create_user_db_returns_the_created_row(db_session):
    user = await create_user_db(
        email="alice@example.com",
        username="alice",
        password_hash="hashed",
        full_name="Alice Founder",
        language="en",
        session=db_session,
    )
    assert user is not None
    assert user.email == "alice@example.com"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_get_user_by_id_db_round_trips(db_session):
    created = await create_user_db(
        email="bob@example.com",
        username="bob",
        password_hash="hashed",
        full_name="Bob Founder",
        session=db_session,
    )
    fetched = await get_user_by_id_db(user_id=created.id, session=db_session)
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_user_by_id_db_returns_none_for_missing_id(db_session):
    fetched = await get_user_by_id_db(user_id=uuid.uuid4(), session=db_session)
    assert fetched is None


@pytest.mark.asyncio
async def test_get_user_by_email_db_is_case_insensitive(db_session):
    await create_user_db(
        email="Carol@Example.com",
        username="carol",
        password_hash="hashed",
        full_name="Carol Founder",
        session=db_session,
    )
    fetched = await get_user_by_email_db(email="carol@example.com", session=db_session)
    assert fetched is not None
    assert fetched.username == "carol"


@pytest.mark.asyncio
async def test_get_user_by_identifier_db_matches_email_username_or_phone(db_session):
    await create_user_db(
        email="dave@example.com",
        username="dave",
        password_hash="hashed",
        full_name="Dave Founder",
        phone="+97455512345",
        session=db_session,
    )
    by_email = await get_user_by_identifier_db(identifier="dave@example.com", session=db_session)
    by_username = await get_user_by_identifier_db(identifier="dave", session=db_session)
    by_phone = await get_user_by_identifier_db(identifier="+97455512345", session=db_session)
    assert by_email is not None and by_username is not None and by_phone is not None
    assert by_email.id == by_username.id == by_phone.id


@pytest.mark.asyncio
async def test_list_users_db_paginates_and_never_raises(db_session):
    for i in range(3):
        await create_user_db(
            email=f"list{i}@example.com",
            username=f"list{i}",
            password_hash="hashed",
            full_name=f"List User {i}",
            session=db_session,
        )
    rows = await list_users_db(limit=2, offset=0, session=db_session)
    assert isinstance(rows, list)
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_update_user_db_changes_fields_and_returns_true(db_session):
    created = await create_user_db(
        email="erin@example.com",
        username="erin",
        password_hash="hashed",
        full_name="Erin Founder",
        session=db_session,
    )
    ok = await update_user_db(user_id=created.id, full_name="Erin Updated", session=db_session)
    assert ok is True
    fetched = await get_user_by_id_db(user_id=created.id, session=db_session)
    assert fetched.full_name == "Erin Updated"


@pytest.mark.asyncio
async def test_update_user_db_returns_false_for_missing_id(db_session):
    ok = await update_user_db(user_id=uuid.uuid4(), full_name="Nobody", session=db_session)
    assert ok is False


@pytest.mark.asyncio
async def test_get_user_by_id_db_degrades_to_none_on_db_error(monkeypatch):
    def _broken_session_factory():
        raise RuntimeError("connection lost")

    import nawa_api.db.utils as utils_module

    monkeypatch.setattr(utils_module, "session_factory", _broken_session_factory)
    result = await get_user_by_id_db(user_id=uuid.uuid4())
    assert result is None
