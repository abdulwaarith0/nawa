"""Shared db-layer helpers: pagination clamping, transactions, relative dates."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.runtime.postgres import session_factory

_LIMIT_MIN, _LIMIT_MAX, _LIMIT_DEFAULT = 1, 100, 20
_OFFSET_MIN, _OFFSET_MAX = 0, 10_000


def clamp_pagination(*, limit: int | None, offset: int | None) -> tuple[int, int]:
    effective_limit = _LIMIT_DEFAULT if limit is None else limit
    effective_offset = 0 if offset is None else offset
    clamped_limit = max(_LIMIT_MIN, min(effective_limit, _LIMIT_MAX))
    clamped_offset = max(_OFFSET_MIN, min(effective_offset, _OFFSET_MAX))
    return clamped_limit, clamped_offset


def days_ago(n: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=n)


def weeks_ago(n: int) -> date:
    return (datetime.now(UTC) - timedelta(weeks=n)).date()


@asynccontextmanager
async def in_transaction() -> AsyncIterator[AsyncSession]:
    """Yields one session with an open transaction shared across composed
    db-function calls: commits on success, rolls back on any exception."""
    async with session_factory() as session:
        async with session.begin():
            yield session


@asynccontextmanager
async def use_session(session: AsyncSession | None) -> AsyncIterator[AsyncSession]:
    """The per-*_db-function session idiom: reuse a caller-provided session
    (composed inside `in_transaction`, caller owns commit/rollback) or open
    and commit a fresh one when called standalone."""
    if session is not None:
        yield session
        return
    async with session_factory() as owned:
        yield owned
        await owned.commit()
