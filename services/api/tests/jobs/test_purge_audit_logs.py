from datetime import UTC, datetime, timedelta

import pytest

from nawa_api.db.audit.create_audit_log_db import create_audit_log_db
from nawa_api.db.audit.list_audit_logs_db import list_audit_logs_db
from nawa_api.jobs.purge_audit_logs import purge_audit_logs


@pytest.mark.asyncio
async def test_purge_removes_only_expired_rows(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    # Bind the global session_factory to the test DB so the job (which opens
    # its own session) hits the throwaway database.
    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)

    past = datetime.now(UTC) - timedelta(days=1)
    future = datetime.now(UTC) + timedelta(days=1)

    await create_audit_log_db(
        action="test.expired", target_type="t", expires_at=past, session=db_session
    )
    await create_audit_log_db(
        action="test.fresh", target_type="t", expires_at=future, session=db_session
    )
    await db_session.commit()

    removed = await purge_audit_logs()
    assert removed >= 1

    remaining = await list_audit_logs_db(session=db_session)
    actions = {r.action for r in remaining}
    assert "test.fresh" in actions
    assert "test.expired" not in actions
