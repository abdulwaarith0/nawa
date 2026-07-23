import asyncio

import pytest

from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.utils.password import hash_password


async def _admin_bearer(client, email="auditadmin@example.com"):
    user = await create_user_db(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("password123"),
        full_name="Audit Admin",
    )
    group = await get_group_by_name_db(name="Administrators")
    await add_group_member_db(group_id=group.id, user_id=user.id)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "password123"},
        headers={"x-client": "mobile", "x-device-id": "audit-dev"},
    )
    return {"authorization": f"Bearer {resp.json()['data']['access_token']}"}


@pytest.mark.asyncio
async def test_audit_logs_requires_permission(client):
    from nawa_api.db.iam.add_group_member_db import add_group_member_db as agm
    from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db as gg
    from nawa_api.db.users.create_user_db import create_user_db as cu

    user = await cu(
        email="auditmember@example.com",
        username="auditmember",
        password_hash=hash_password("password123"),
        full_name="Audit Member",
    )
    members = await gg(name="Members")
    await agm(group_id=members.id, user_id=user.id)
    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "auditmember@example.com", "password": "password123"},
        headers={"x-client": "mobile", "x-device-id": "am-dev"},
    )
    headers = {"authorization": f"Bearer {login.json()['data']['access_token']}"}
    resp = await client.get("/api/v1/audit-logs", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_trail_records_policy_create(client):
    headers = await _admin_bearer(client)
    create = await client.post(
        "/api/v1/iam/policies",
        json={"name": "AuditTestPolicy", "statements": []},
        headers=headers,
    )
    assert create.status_code == 201

    # @audited fires fire-and-forget; give the scheduled task a moment.
    await asyncio.sleep(0.2)
    logs = await client.get("/api/v1/audit-logs?action=iam.policy.create", headers=headers)
    assert logs.status_code == 200
    actions = {row["action"] for row in logs.json()["data"]}
    assert "iam.policy.create" in actions


@pytest.mark.asyncio
async def test_sse_requires_session(client):
    resp = await client.get("/api/v1/events")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_publish_event_never_raises():
    from nawa_api.utils.publish_event import publish_event

    # Should not raise even if no subscribers.
    await publish_event("events:notifications:nobody", {"t": "ping"})
