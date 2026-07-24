import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.models.identity import AuditLog
from nawa_api.services.audit.create_audit_log import create_audit_log
from nawa_api.utils.password import hash_password


@pytest_asyncio.fixture
async def bound(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    return db_session


async def _real_user(session):
    email = f"{uuid.uuid4().hex[:8]}@x.io"
    return await create_user_db(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("password123"),
        full_name="Actor",
        session=session,
    )


@pytest.mark.asyncio
async def test_body_containing_a_raw_uuid_field_still_persists(bound):
    # Regression: a caller passing `SomeInput.model_dump()` (not
    # `mode="json"`) leaves UUID fields as live UUID objects — Postgres's
    # JSONB write used to choke on that with a bare TypeError, and
    # create_audit_log_db's except-and-log-only convention swallowed the
    # whole row silently. Found live: every "accept" decision's cohort_id
    # meant its audit row never got written at all.
    actor = await _real_user(bound)
    await bound.commit()
    action = f"test.action.{uuid.uuid4().hex[:8]}"
    cohort_id = uuid.uuid4()

    await create_audit_log(
        action=action,
        target_type="intake_application",
        actor_id=actor.id,
        body={"decision": "accept", "cohort_id": cohort_id},
    )

    row = (
        await bound.execute(select(AuditLog).where(AuditLog.action == action))
    ).scalar_one_or_none()
    assert row is not None
    assert row.audit_metadata["body"]["cohort_id"] == str(cohort_id)


@pytest.mark.asyncio
async def test_body_without_exotic_types_persists_unchanged(bound):
    action = f"test.action.{uuid.uuid4().hex[:8]}"

    await create_audit_log(
        action=action,
        target_type="intake_application",
        body={"decision": "reject", "reason": "not a fit"},
    )

    row = (
        await bound.execute(select(AuditLog).where(AuditLog.action == action))
    ).scalar_one_or_none()
    assert row is not None
    assert row.audit_metadata["body"] == {"decision": "reject", "reason": "not a fit"}
