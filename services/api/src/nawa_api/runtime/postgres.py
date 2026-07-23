"""The one and only Postgres engine + session factory in the codebase.

Nothing outside `db/`, `seed.py`, and this module constructs an engine,
a sessionmaker, or acquires a raw session.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from nawa_api.runtime.settings import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
)

session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def connect_postgres(*, timeout_seconds: float = 5.0) -> None:
    """Boot probe: raises if Postgres is unreachable. Fatal at boot per architecture."""

    async def _ping() -> None:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    await asyncio.wait_for(_ping(), timeout=timeout_seconds)
