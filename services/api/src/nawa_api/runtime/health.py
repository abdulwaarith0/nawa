"""Readiness probes: real Postgres SELECT 1 + Redis PING, each 2 s timeout.

Returns (ok, failing_dependency|None). Credentials are never included in the
failing-dependency string.
"""

import asyncio

from sqlalchemy import text

from nawa_api.runtime.postgres import engine
from nawa_api.runtime.redis import get_redis

_PROBE_TIMEOUT = 2.0


async def _check_postgres() -> bool:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True


async def _check_redis() -> bool:
    await get_redis().ping()
    return True


async def check_readiness() -> tuple[bool, str | None]:
    try:
        await asyncio.wait_for(_check_postgres(), timeout=_PROBE_TIMEOUT)
    except Exception:
        return False, "postgres unreachable"
    try:
        await asyncio.wait_for(_check_redis(), timeout=_PROBE_TIMEOUT)
    except Exception:
        return False, "redis unreachable"
    return True, None
