import pytest
from pydantic import BaseModel

from nawa_api.runtime.redis import (
    connect_redis,
    get_redis,
    redact_redis_url,
    redis_retrieve_key,
    redis_update_key,
)


class _Sample(BaseModel):
    name: str
    count: int


@pytest.mark.asyncio
async def test_get_redis_returns_a_singleton():
    a = get_redis()
    b = get_redis()
    assert a is b


@pytest.mark.asyncio
async def test_connect_redis_succeeds_against_live_redis():
    await connect_redis()


@pytest.mark.asyncio
async def test_connect_redis_raises_on_unreachable_redis():
    from redis.asyncio import from_url

    dead = from_url("redis://localhost:1/0")
    with pytest.raises(Exception):
        await dead.ping()
    await dead.aclose()


@pytest.mark.asyncio
async def test_redis_update_and_retrieve_round_trips_a_model():
    key = "test:runtime:redis:sample"
    redis = get_redis()
    try:
        await redis_update_key(key, _Sample(name="nawa", count=3), ttl_seconds=30)
        got = await redis_retrieve_key(key, _Sample)
        assert got == _Sample(name="nawa", count=3)
    finally:
        await redis.delete(key)


@pytest.mark.asyncio
async def test_redis_retrieve_key_returns_none_on_miss():
    got = await redis_retrieve_key("test:runtime:redis:does-not-exist", _Sample)
    assert got is None


@pytest.mark.asyncio
async def test_redis_retrieve_key_returns_none_on_garbage_payload():
    key = "test:runtime:redis:garbage"
    redis = get_redis()
    try:
        await redis.set(key, "not-json-at-all")
        got = await redis_retrieve_key(key, _Sample)
        assert got is None
    finally:
        await redis.delete(key)


def test_redact_redis_url_hides_credentials():
    assert redact_redis_url("redis://user:secret@localhost:6379/0") == (
        "redis://user:***@localhost:6379/0"
    )


def test_redact_redis_url_passthrough_without_credentials():
    assert redact_redis_url("redis://localhost:6379/0") == "redis://localhost:6379/0"
