import pytest

from nawa_api.db.ai_calls.create_ai_call_db import create_ai_call_db
from nawa_api.db.audit.create_audit_log_db import create_audit_log_db
from nawa_api.db.notifications.create_notification_db import create_notification_db
from nawa_api.db.site_config.get_site_config_db import get_site_config_db
from nawa_api.db.site_config.upsert_site_config_db import upsert_site_config_db
from nawa_api.db.users.create_user_db import create_user_db


@pytest.mark.asyncio
async def test_create_notification_db(db_session):
    user = await create_user_db(
        email="notify@example.com",
        username="notifyuser",
        password_hash="hashed",
        full_name="Notify User",
        session=db_session,
    )
    notif = await create_notification_db(
        user_id=user.id,
        kind="request.match",
        title_en="New match for your request",
        payload={"surface": "requests", "id": "abc"},
        session=db_session,
    )
    assert notif is not None
    assert notif.read_at is None


@pytest.mark.asyncio
async def test_create_audit_log_db_sets_expiry(db_session):
    user = await create_user_db(
        email="audituser@example.com",
        username="audituser",
        password_hash="hashed",
        full_name="Audit User",
        session=db_session,
    )
    log = await create_audit_log_db(
        actor_id=user.id,
        action="auth.signup",
        target_type="user",
        target_id=user.id,
        status_code=201,
        session=db_session,
    )
    assert log is not None
    assert log.expires_at > log.created_at


@pytest.mark.asyncio
async def test_create_ai_call_db(db_session):
    call = await create_ai_call_db(
        task="intake.score",
        provider="mock",
        model="mock-large",
        prompt_hash="deadbeef",
        prompt_version="v1",
        status="ok",
        tokens_in=100,
        tokens_out=50,
        cost_estimate=0.002,
        latency_ms=350,
        session=db_session,
    )
    assert call is not None
    assert call.status == "ok"


@pytest.mark.asyncio
async def test_site_config_upsert_and_get_roundtrip(db_session):
    ok = await upsert_site_config_db(key="rate_limiting_enabled", value=True, session=db_session)
    assert ok is True
    value = await get_site_config_db(key="rate_limiting_enabled", session=db_session)
    assert value is True

    ok2 = await upsert_site_config_db(key="rate_limiting_enabled", value=False, session=db_session)
    assert ok2 is True
    value2 = await get_site_config_db(key="rate_limiting_enabled", session=db_session)
    assert value2 is False


@pytest.mark.asyncio
async def test_get_site_config_db_returns_none_for_missing_key(db_session):
    value = await get_site_config_db(key="does-not-exist", session=db_session)
    assert value is None
