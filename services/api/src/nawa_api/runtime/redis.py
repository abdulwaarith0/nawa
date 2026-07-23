"""The one process-wide Redis client. Never construct ad-hoc clients elsewhere."""

from __future__ import annotations

import asyncio
import re

from pydantic import BaseModel
from redis.asyncio import Redis, from_url

from nawa_api.runtime.settings import get_settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = from_url(get_settings().redis_url, decode_responses=True)
    return _redis


async def connect_redis(*, timeout_seconds: float = 5.0) -> None:
    """Boot probe: raises if Redis is unreachable. Fatal at boot, no in-memory fallback."""
    await asyncio.wait_for(get_redis().ping(), timeout=timeout_seconds)


async def redis_retrieve_key[T: BaseModel](key: str, model_type: type[T]) -> T | None:
    raw = await get_redis().get(key)
    if raw is None:
        return None
    try:
        return model_type.model_validate_json(raw)
    except Exception:
        return None


async def redis_update_key(key: str, value: BaseModel, ttl_seconds: int) -> None:
    await get_redis().setex(key, ttl_seconds, value.model_dump_json())


def redact_redis_url(url: str) -> str:
    """Replaces credentials in a redis:// URL with '***' before it ever hits a log line."""
    return re.sub(r"(://[^:/@]+:)[^@]+(@)", r"\1***\2", url)
