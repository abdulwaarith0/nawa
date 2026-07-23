"""Runs the full seed script against the throwaway test database and asserts
the headline counts from 03-data-spine.md §9. This also doubles as the
seed_data package's integration coverage."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from nawa_api.models.identity import User
from nawa_api.models.intake import Application, DedupMatch
from nawa_api.models.journey import ResourceChunk
from nawa_api.models.profiles import FounderProfile
from nawa_api.models.programs import Program
from nawa_api.models.reports import Anomaly, KpiEntry
from nawa_api.runtime.settings import get_settings


class _FakeSettings:
    def __init__(self, database_url: str):
        self.database_url = database_url


@pytest.mark.asyncio
async def test_seed_produces_expected_headline_counts(test_db_name, monkeypatch):
    base_settings = get_settings()
    test_url = f"{base_settings.database_url.rsplit('/', 1)[0]}/{test_db_name}"
    test_engine = create_async_engine(test_url, pool_pre_ping=True)
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    # Redirect every db-layer call and the seed's own truncate/safety-check
    # onto the throwaway test database instead of the real dev one.
    monkeypatch.setattr("nawa_api.db.utils.session_factory", test_session_factory)
    monkeypatch.setattr("nawa_api.seed.engine", test_engine)
    monkeypatch.setattr("nawa_api.seed.get_settings", lambda: _FakeSettings(database_url=test_url))

    from nawa_api.seed import run_seed

    await run_seed()

    async with test_session_factory() as session:
        program_count = (
            await session.execute(select(func.count()).select_from(Program))
        ).scalar_one()
        app_count = (
            await session.execute(select(func.count()).select_from(Application))
        ).scalar_one()
        profile_count = (
            await session.execute(select(func.count()).select_from(FounderProfile))
        ).scalar_one()
        kpi_entry_count = (
            await session.execute(select(func.count()).select_from(KpiEntry))
        ).scalar_one()
        chunk_count = (
            await session.execute(select(func.count()).select_from(ResourceChunk))
        ).scalar_one()
        user_count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
        dedup_count = (
            await session.execute(select(func.count()).select_from(DedupMatch))
        ).scalar_one()
        anomaly_count = (
            await session.execute(select(func.count()).select_from(Anomaly))
        ).scalar_one()

    await test_engine.dispose()

    assert program_count == 6
    assert app_count == 220
    assert profile_count == 50
    assert kpi_entry_count >= 6000
    assert chunk_count >= 250
    assert user_count >= 57
    assert dedup_count >= 8
    assert anomaly_count == 10


@pytest.mark.asyncio
async def test_seed_is_idempotent_across_two_runs(test_db_name, monkeypatch):
    base_settings = get_settings()
    test_url = f"{base_settings.database_url.rsplit('/', 1)[0]}/{test_db_name}"
    test_engine = create_async_engine(test_url, pool_pre_ping=True)
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    monkeypatch.setattr("nawa_api.db.utils.session_factory", test_session_factory)
    monkeypatch.setattr("nawa_api.seed.engine", test_engine)
    monkeypatch.setattr("nawa_api.seed.get_settings", lambda: _FakeSettings(database_url=test_url))

    from nawa_api.seed import run_seed

    await run_seed()
    async with test_session_factory() as session:
        first_count = (
            await session.execute(select(func.count()).select_from(Application))
        ).scalar_one()

    await run_seed()
    async with test_session_factory() as session:
        second_count = (
            await session.execute(select(func.count()).select_from(Application))
        ).scalar_one()

    await test_engine.dispose()
    assert first_count == second_count == 220


@pytest.mark.asyncio
async def test_seed_refuses_unsafe_database_name(monkeypatch):
    monkeypatch.setattr(
        "nawa_api.seed.get_settings",
        lambda: _FakeSettings(
            database_url="postgresql+asyncpg://nawa:nawa@localhost:5433/nawa_production"
        ),
    )
    from nawa_api.seed import run_seed

    with pytest.raises(SystemExit) as exc_info:
        await run_seed()
    assert exc_info.value.code == 1
