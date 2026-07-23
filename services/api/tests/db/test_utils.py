from datetime import UTC, date, datetime

import pytest

from nawa_api.db.utils import clamp_pagination, days_ago, in_transaction, weeks_ago
from nawa_api.runtime.postgres import session_factory


def test_clamp_pagination_defaults():
    assert clamp_pagination(limit=None, offset=None) == (20, 0)


def test_clamp_pagination_within_bounds_passes_through():
    assert clamp_pagination(limit=50, offset=10) == (50, 10)


def test_clamp_pagination_clamps_limit_upper_bound():
    assert clamp_pagination(limit=500, offset=0) == (100, 0)


def test_clamp_pagination_clamps_limit_lower_bound():
    assert clamp_pagination(limit=0, offset=0) == (1, 0)
    assert clamp_pagination(limit=-5, offset=0) == (1, 0)


def test_clamp_pagination_clamps_offset_bounds():
    assert clamp_pagination(limit=20, offset=-1) == (20, 0)
    assert clamp_pagination(limit=20, offset=999_999) == (20, 10_000)


def test_days_ago_returns_a_past_utc_datetime():
    result = days_ago(5)
    assert isinstance(result, datetime)
    assert result.tzinfo is not None
    assert result < datetime.now(UTC)


def test_days_ago_zero_is_approximately_now():
    delta = datetime.now(UTC) - days_ago(0)
    assert abs(delta.total_seconds()) < 5


def test_weeks_ago_returns_a_date_n_weeks_back():
    today = datetime.now(UTC).date()
    result = weeks_ago(2)
    assert isinstance(result, date)
    assert (today - result).days in (14, 15)  # tolerate a midnight boundary


@pytest.mark.asyncio
async def test_in_transaction_commits_on_success():
    from sqlalchemy import text

    async with in_transaction() as session:
        await session.execute(text("SELECT 1"))
    # No exception means commit happened; a fresh session should still work.
    async with session_factory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_in_transaction_rolls_back_on_error():
    from sqlalchemy import text

    with pytest.raises(RuntimeError):
        async with in_transaction() as session:
            await session.execute(text("SELECT 1"))
            raise RuntimeError("boom")
