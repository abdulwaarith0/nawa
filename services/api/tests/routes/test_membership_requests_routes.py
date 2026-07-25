import asyncio

import pytest

from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.runtime.redis import get_redis
from nawa_api.utils.password import hash_password


async def _admin(client, email="accessadmin@example.com"):
    user = await create_user_db(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("password123"),
        full_name="Access Admin",
    )
    group = await get_group_by_name_db(name="Administrators")
    await add_group_member_db(group_id=group.id, user_id=user.id)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "password123"},
        headers={"x-client": "mobile", "x-device-id": "access-dev"},
    )
    return {"authorization": f"Bearer {resp.json()['data']['access_token']}"}


async def _member_headers(client, email="member1@example.com"):
    user = await create_user_db(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("password123"),
        full_name="Plain Member",
    )
    members = await get_group_by_name_db(name="Members")
    await add_group_member_db(group_id=members.id, user_id=user.id)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "password123"},
        headers={"x-client": "mobile", "x-device-id": "member-dev"},
    )
    return {"authorization": f"Bearer {resp.json()['data']['access_token']}"}


@pytest.mark.asyncio
async def test_request_access_returns_ok_and_no_data(client):
    resp = await client.post(
        "/api/v1/auth/request-access",
        json={"full_name": "Alice Founder", "email": "alice@example.com", "reason": "join"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] is None
    await asyncio.sleep(0.2)  # let the @audited fire-and-forget task settle


@pytest.mark.asyncio
async def test_request_access_is_non_enumerable_for_existing_accounts(client):
    await create_user_db(
        email="hasaccount@example.com",
        username="hasaccount",
        password_hash=hash_password("password123"),
        full_name="Has Account",
    )
    resp = await client.post(
        "/api/v1/auth/request-access",
        json={"full_name": "Someone", "email": "hasaccount@example.com"},
    )
    # Identical 200/None response whether or not the email already has an account.
    assert resp.status_code == 200
    assert resp.json()["data"] is None
    await asyncio.sleep(0.2)


@pytest.mark.asyncio
async def test_request_access_rejects_invalid_body(client):
    resp = await client.post("/api/v1/auth/request-access", json={"full_name": "", "email": ""})
    assert resp.status_code == 400
    await asyncio.sleep(0.2)


@pytest.mark.asyncio
async def test_list_access_requests_requires_permission(client):
    headers = await _member_headers(client)
    resp = await client.get("/api/v1/admin/access-requests", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_access_requests_returns_submitted_requests(client):
    headers = await _admin(client)
    await client.post(
        "/api/v1/auth/request-access",
        json={"full_name": "Bob Founder", "email": "bob2@example.com"},
    )
    resp = await client.get("/api/v1/admin/access-requests", headers=headers)
    assert resp.status_code == 200
    emails = {row["email"] for row in resp.json()["data"]}
    assert "bob2@example.com" in emails
    await asyncio.sleep(0.2)


@pytest.mark.asyncio
async def test_list_access_requests_filters_by_status(client):
    headers = await _admin(client)
    await client.post(
        "/api/v1/auth/request-access",
        json={"full_name": "Carol Founder", "email": "carol2@example.com"},
    )
    resp = await client.get(
        "/api/v1/admin/access-requests", params={"status": "rejected"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []
    await asyncio.sleep(0.2)


@pytest.mark.asyncio
async def test_approve_creates_settable_account_end_to_end(client):
    headers = await _admin(client)
    await client.post(
        "/api/v1/auth/request-access",
        json={"full_name": "Dave Founder", "email": "dave2@example.com", "reason": "join"},
    )
    listed = await client.get("/api/v1/admin/access-requests", headers=headers)
    request_id = next(
        row["id"] for row in listed.json()["data"] if row["email"] == "dave2@example.com"
    )

    approved = await client.post(
        f"/api/v1/admin/access-requests/{request_id}/approve", headers=headers
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "approved"

    # A real reset code exists via the reused password-reset mechanism.
    code = await get_redis().get("auth:reset:dave2@example.com")
    assert code is not None

    reset = await client.post(
        "/api/v1/auth/reset-password",
        json={"identifier": "dave2@example.com", "code": code, "new_password": "newpassword1"},
    )
    assert reset.status_code == 200

    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "dave2@example.com", "password": "newpassword1"},
    )
    assert login.status_code == 200
    assert set(login.json()["data"]["effective"]) == {"nawa:profiles:write", "nawa:community:read"}

    # Audit log recorded the approval.
    await asyncio.sleep(0.2)
    logs = await client.get(
        "/api/v1/audit-logs?action=admin.access_request.approve", headers=headers
    )
    assert any(row["target_type"] == "membership_request" for row in logs.json()["data"])


@pytest.mark.asyncio
async def test_approve_twice_conflicts(client):
    headers = await _admin(client)
    await client.post(
        "/api/v1/auth/request-access",
        json={"full_name": "Erin Founder", "email": "erin2@example.com"},
    )
    listed = await client.get("/api/v1/admin/access-requests", headers=headers)
    request_id = next(
        row["id"] for row in listed.json()["data"] if row["email"] == "erin2@example.com"
    )
    first = await client.post(
        f"/api/v1/admin/access-requests/{request_id}/approve", headers=headers
    )
    assert first.status_code == 200
    second = await client.post(
        f"/api/v1/admin/access-requests/{request_id}/approve", headers=headers
    )
    assert second.status_code == 409
    await asyncio.sleep(0.2)


@pytest.mark.asyncio
async def test_reject_marks_rejected_and_no_account_is_created(client):
    headers = await _admin(client)
    await client.post(
        "/api/v1/auth/request-access",
        json={"full_name": "Frank Founder", "email": "frank2@example.com"},
    )
    listed = await client.get("/api/v1/admin/access-requests", headers=headers)
    request_id = next(
        row["id"] for row in listed.json()["data"] if row["email"] == "frank2@example.com"
    )

    rejected = await client.post(
        f"/api/v1/admin/access-requests/{request_id}/reject", headers=headers
    )
    assert rejected.status_code == 200
    assert rejected.json()["data"]["status"] == "rejected"

    login_attempt = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "frank2@example.com", "password": "whatever12"},
    )
    assert login_attempt.status_code == 401  # no account was ever created
    await asyncio.sleep(0.2)


@pytest.mark.asyncio
async def test_approve_and_reject_require_permission(client):
    headers = await _member_headers(client)
    resp = await client.post(
        "/api/v1/admin/access-requests/00000000-0000-0000-0000-000000000000/approve",
        headers=headers,
    )
    assert resp.status_code == 403
    resp = await client.post(
        "/api/v1/admin/access-requests/00000000-0000-0000-0000-000000000000/reject",
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_approve_missing_request_is_404(client):
    headers = await _admin(client)
    resp = await client.post(
        "/api/v1/admin/access-requests/00000000-0000-0000-0000-000000000000/approve",
        headers=headers,
    )
    assert resp.status_code == 404
    await asyncio.sleep(0.2)


@pytest.mark.asyncio
async def test_request_access_is_rate_limited(client):
    last = None
    for i in range(11):
        last = await client.post(
            "/api/v1/auth/request-access",
            json={"full_name": "Spammer", "email": f"spam{i}@example.com"},
        )
    assert last.status_code == 429
    assert last.headers.get("retry-after") is not None
    await asyncio.sleep(0.2)
