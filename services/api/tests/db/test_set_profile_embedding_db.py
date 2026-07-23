import uuid

import pytest

from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.profiles.get_profile_by_id_any_status_db import get_profile_by_id_any_status_db
from nawa_api.db.profiles.set_profile_embedding_db import set_profile_embedding_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.runtime.settings import get_settings

_DIM = get_settings().embeddings_dimension


@pytest.mark.asyncio
async def test_set_profile_embedding_db_updates_and_clears_stale_flag(db_session):
    user = await create_user_db(
        email="embed@example.com",
        username="embeduser",
        password_hash="hashed",
        full_name="Embed User",
        session=db_session,
    )
    profile = await create_founder_profile_db(
        user_id=user.id,
        handle="embed-founder",
        display_name_en="Embed Founder",
        session=db_session,
    )
    assert profile.embedding_stale is True

    vector = [0.1] * _DIM
    ok = await set_profile_embedding_db(
        profile_id=profile.id, embedding=vector, embedding_model="mock", session=db_session
    )
    assert ok is True

    fetched = await get_profile_by_id_any_status_db(profile_id=profile.id, session=db_session)
    assert fetched.embedding_stale is False
    assert fetched.embedding_model == "mock"


@pytest.mark.asyncio
async def test_set_profile_embedding_db_returns_false_for_missing_profile(db_session):
    ok = await set_profile_embedding_db(
        profile_id=uuid.uuid4(),
        embedding=[0.0] * _DIM,
        embedding_model="mock",
        session=db_session,
    )
    assert ok is False
