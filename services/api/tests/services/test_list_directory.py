"""services.community.list_directory: cache hit/miss, deterministic hashing
of filter params (array order must not matter), and the never-cache-empty
rule (08-community-hub.md §3.3)."""

import pytest_asyncio

from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.runtime.redis import get_redis
from nawa_api.services.community import list_directory as directory_mod
from nawa_api.services.community.list_directory import cache_key, list_directory
from tests.db.factories import make_profile


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


def test_cache_key_is_deterministic_regardless_of_array_order():
    key_a = cache_key(
        q=None,
        domains=None,
        skills=["b", "a"],
        sector=None,
        country=None,
        program_id=None,
        stage=None,
        mentors=None,
        limit=20,
        offset=0,
    )
    key_b = cache_key(
        q=None,
        domains=None,
        skills=["a", "b"],
        sector=None,
        country=None,
        program_id=None,
        stage=None,
        mentors=None,
        limit=20,
        offset=0,
    )
    assert key_a == key_b


def test_cache_key_treats_absent_and_false_mentors_the_same():
    key_absent = cache_key(
        q=None,
        domains=None,
        skills=None,
        sector=None,
        country=None,
        program_id=None,
        stage=None,
        mentors=None,
        limit=20,
        offset=0,
    )
    key_false = cache_key(
        q=None,
        domains=None,
        skills=None,
        sector=None,
        country=None,
        program_id=None,
        stage=None,
        mentors=False,
        limit=20,
        offset=0,
    )
    assert key_absent == key_false


def test_cache_key_changes_when_a_filter_changes():
    base = cache_key(
        q=None,
        domains=None,
        skills=None,
        sector=None,
        country=None,
        program_id=None,
        stage=None,
        mentors=None,
        limit=20,
        offset=0,
    )
    changed = cache_key(
        q=None,
        domains=None,
        skills=None,
        sector="agtech",
        country=None,
        program_id=None,
        stage=None,
        mentors=None,
        limit=20,
        offset=0,
    )
    assert base != changed


async def test_empty_result_is_never_cached(bound):
    items = await list_directory(sector="no-such-sector-xyz")
    assert items == []
    key = cache_key(
        q=None,
        domains=None,
        skills=None,
        sector="no-such-sector-xyz",
        country=None,
        program_id=None,
        stage=None,
        mentors=None,
        limit=20,
        offset=0,
    )
    assert await get_redis().get(key) is None


async def test_result_is_cached_until_invalidated(bound, monkeypatch):
    user = await create_user_db(
        email="cache@example.com",
        username="cacheuser",
        password_hash="h",
        full_name="F",
        session=bound,
    )
    await make_profile(bound, user_id=user.id, handle="cache-founder")
    await bound.commit()

    first = await list_directory()
    assert len(first) == 1

    calls = {"n": 0}
    real = directory_mod.list_directory_db

    async def counting(*args, **kwargs):
        calls["n"] += 1
        return await real(*args, **kwargs)

    monkeypatch.setattr(directory_mod, "list_directory_db", counting)
    second = await list_directory()
    assert second == first
    assert calls["n"] == 0


async def test_array_param_order_hits_same_cache_row(bound, monkeypatch):
    user = await create_user_db(
        email="order@example.com",
        username="orderuser",
        password_hash="h",
        full_name="F",
        session=bound,
    )
    profile = await make_profile(bound, user_id=user.id, handle="order-founder")
    profile.skills = ["a", "b"]
    await bound.commit()

    first = await list_directory(skills=["b", "a"])
    calls = {"n": 0}
    real = directory_mod.list_directory_db

    async def counting(*args, **kwargs):
        calls["n"] += 1
        return await real(*args, **kwargs)

    monkeypatch.setattr(directory_mod, "list_directory_db", counting)
    second = await list_directory(skills=["a", "b"])
    assert second == first
    assert calls["n"] == 0
