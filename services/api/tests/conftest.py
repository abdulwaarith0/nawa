"""Root pytest configuration.

asyncpg is incompatible with Windows' default ProactorEventLoop (it needs
socket primitives Proactor doesn't implement), so on win32 we force the
SelectorEventLoop policy before any event loop is created. Non-Windows
platforms are unaffected.
"""

import asyncio
import os
import sys
import uuid

# The test environment is set BEFORE any nawa_api import so the cached settings
# object binds to test infra (a strong JWT secret, Redis logical db 15).
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-at-least-32-chars-long-000")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from alembic import command  # noqa: E402
from nawa_api.runtime.db_guard import TEST_DB_PREFIX, is_seed_safe_db_name  # noqa: E402
from nawa_api.runtime.settings import get_settings  # noqa: E402

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _admin_url(maintenance_db: str = "postgres") -> str:
    settings = get_settings()
    base = settings.database_url.rsplit("/", 1)[0]
    return f"{base}/{maintenance_db}"


@pytest_asyncio.fixture(scope="session")
async def test_db_name() -> str:
    """Creates a throwaway nawa_test_<uuid> database, migrates it to head,
    yields its name, and drops it in a `finally` that survives failure."""
    name = f"{TEST_DB_PREFIX}{uuid.uuid4().hex[:12]}"
    assert is_seed_safe_db_name(name), "generated test db name must pass the safety guard"

    admin_engine = create_async_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    await admin_engine.dispose()

    settings = get_settings()
    test_url = f"{settings.database_url.rsplit('/', 1)[0]}/{name}"

    try:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.attributes["sqlalchemy.url"] = test_url
        # alembic's async env.py calls asyncio.run() internally, which cannot
        # be invoked from within a loop already running (this fixture's own).
        # Running it in a worker thread gives it a loop-free thread to do so.
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
        yield name
    finally:
        admin_engine = create_async_engine(_admin_url(), isolation_level="AUTOCOMMIT")
        async with admin_engine.connect() as conn:
            await conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        await admin_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_engine(test_db_name: str):
    settings = get_settings()
    test_url = f"{settings.database_url.rsplit('/', 1)[0]}/{test_db_name}"
    engine = create_async_engine(test_url, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(test_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


async def _truncate_all(engine) -> None:
    from nawa_api.models import Base

    names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    async with engine.connect() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
        await conn.commit()


@pytest_asyncio.fixture()
async def client(test_engine, monkeypatch):
    """An httpx AsyncClient over the app, wired to the throwaway test DB and an
    isolated Redis (logical db 15), with IAM builtins seeded. Truncates the
    schema first for per-test isolation."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)

    from nawa_api.runtime.redis import get_redis

    redis = get_redis()
    await redis.flushdb()
    await _truncate_all(test_engine)

    from nawa_api.services.iam.seed_defaults import seed_defaults

    await seed_defaults()

    from httpx import ASGITransport, AsyncClient

    from nawa_api.runtime.app_factory import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await redis.flushdb()


def test_harness_refuses_unsafe_db_name():
    """Meta-test: the safety guard rejects anything not nawa_dev/nawa_test_*."""
    assert is_seed_safe_db_name("nawa_prod") is False
    assert is_seed_safe_db_name("postgres") is False


@pytest.mark.asyncio
async def test_harness_db_name_is_prefixed_correctly(test_db_name: str):
    assert test_db_name.startswith(TEST_DB_PREFIX)
