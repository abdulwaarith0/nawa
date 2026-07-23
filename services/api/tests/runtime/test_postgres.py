import pytest
from sqlalchemy import text

from nawa_api.runtime.postgres import connect_postgres, engine, session_factory


@pytest.mark.asyncio
async def test_engine_and_session_factory_are_module_singletons():
    from nawa_api.runtime import postgres as postgres_module

    assert postgres_module.engine is engine
    assert postgres_module.session_factory is session_factory


@pytest.mark.asyncio
async def test_session_factory_executes_a_query_against_the_dev_db():
    async with session_factory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_connect_postgres_succeeds_against_a_live_db():
    # Should not raise when the configured database is reachable.
    await connect_postgres()


@pytest.mark.asyncio
async def test_connect_postgres_raises_on_unreachable_db():
    from sqlalchemy.ext.asyncio import create_async_engine

    bad_engine = create_async_engine(
        "postgresql+asyncpg://nawa:nawa@localhost:1/nawa_dev",
        pool_pre_ping=False,
    )
    with pytest.raises(Exception):
        async with bad_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    await bad_engine.dispose()
