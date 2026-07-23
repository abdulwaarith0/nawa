import pytest

from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.site_config.upsert_site_config_db import upsert_site_config_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.runtime.redis import get_redis
from nawa_api.utils.password import hash_password


async def _admin(client, email="siteadmin@example.com"):
    user = await create_user_db(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("password123"),
        full_name="Site Admin",
    )
    group = await get_group_by_name_db(name="Administrators")
    await add_group_member_db(group_id=group.id, user_id=user.id)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "password123"},
        headers={"x-client": "mobile", "x-device-id": "site-dev"},
    )
    return {"authorization": f"Bearer {resp.json()['data']['access_token']}"}


@pytest.mark.asyncio
async def test_public_site_config_projection(client):
    await upsert_site_config_db(key="maintenance_mode", value=False)
    await upsert_site_config_db(key="audit_enabled", value=True)
    resp = await client.get("/api/v1/site-config")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "maintenance_mode" in data
    assert "audit_enabled" not in data  # not in the public projection


@pytest.mark.asyncio
async def test_admin_site_config_get_and_patch(client):
    headers = await _admin(client)
    await upsert_site_config_db(key="rate_limiting_enabled", value=True)

    got = await client.get("/api/v1/admin/site-config", headers=headers)
    assert got.status_code == 200
    assert "rate_limiting_enabled" in got.json()["data"]

    patched = await client.patch(
        "/api/v1/admin/site-config",
        json={"key": "rate_limiting_enabled", "value": False},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["rate_limiting_enabled"] is False


@pytest.mark.asyncio
async def test_admin_site_config_requires_permission(client):
    user = await create_user_db(
        email="sitemember@example.com",
        username="sitemember",
        password_hash=hash_password("password123"),
        full_name="Site Member",
    )
    members = await get_group_by_name_db(name="Members")
    await add_group_member_db(group_id=members.id, user_id=user.id)
    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "sitemember@example.com", "password": "password123"},
        headers={"x-client": "mobile", "x-device-id": "sm-dev"},
    )
    headers = {"authorization": f"Bearer {login.json()['data']['access_token']}"}
    resp = await client.get("/api/v1/admin/site-config", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_password_reset_flow(client):
    await create_user_db(
        email="reset@example.com",
        username="resetuser",
        password_hash=hash_password("oldpassword1"),
        full_name="Reset User",
    )
    # forgot-password stores a code in Redis (dev never returns it in the body)
    forgot = await client.post(
        "/api/v1/auth/forgot-password", json={"identifier": "reset@example.com"}
    )
    assert forgot.status_code == 200
    assert "code" not in (forgot.json().get("data") or {})

    code = await get_redis().get("auth:reset:reset@example.com")
    assert code is not None

    reset = await client.post(
        "/api/v1/auth/reset-password",
        json={"identifier": "reset@example.com", "code": code, "new_password": "newpassword1"},
    )
    assert reset.status_code == 200

    # Old password no longer works; new one does.
    old = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "reset@example.com", "password": "oldpassword1"},
    )
    assert old.status_code == 401
    new = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "reset@example.com", "password": "newpassword1"},
    )
    assert new.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_wrong_code_rejected(client):
    await create_user_db(
        email="reset2@example.com",
        username="reset2user",
        password_hash=hash_password("oldpassword1"),
        full_name="Reset2 User",
    )
    await client.post("/api/v1/auth/forgot-password", json={"identifier": "reset2@example.com"})
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"identifier": "reset2@example.com", "code": "000000", "new_password": "newpassword1"},
    )
    assert resp.status_code == 400
