"""Idempotent one-shot boot guarded by a module flag."""

import asyncio

from nawa_api.runtime.postgres import connect_postgres
from nawa_api.runtime.redis import connect_redis
from nawa_api.services.iam.seed_defaults import seed_defaults
from nawa_api.utils.logger import get_logger

_booted = False


async def bootstrap() -> None:
    global _booted
    if _booted:
        return

    # Parallel connect; either failure is fatal (the callers exit non-zero).
    await asyncio.gather(connect_postgres(), connect_redis())

    # IAM builtins — loud but non-fatal; self-heals next boot.
    try:
        await seed_defaults()
    except Exception:
        get_logger().error("seed_defaults_failed", exc_info=True)

    _booted = True
