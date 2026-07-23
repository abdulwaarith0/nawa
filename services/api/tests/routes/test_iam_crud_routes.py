import pytest

from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.iam.get_policy_by_name_db import get_policy_by_name_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.utils.password import hash_password


async def _admin(client, email="crudadmin@example.com"):
    user = await create_user_db(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("password123"),
        full_name="Crud Admin",
    )
    group = await get_group_by_name_db(name="Administrators")
    await add_group_member_db(group_id=group.id, user_id=user.id)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "password123"},
        headers={"x-client": "mobile", "x-device-id": "crud-dev"},
    )
    return {"authorization": f"Bearer {resp.json()['data']['access_token']}"}, user


@pytest.mark.asyncio
async def test_permissions_catalog(client):
    headers, _ = await _admin(client)
    resp = await client.get("/api/v1/iam/permissions", headers=headers)
    assert resp.status_code == 200
    perms = resp.json()["data"]["permissions"]
    assert "nawa:iam:manage" in perms


@pytest.mark.asyncio
async def test_policy_get_update_delete_lifecycle(client):
    headers, _ = await _admin(client)
    created = await client.post(
        "/api/v1/iam/policies",
        json={"name": "CustomPolicy", "statements": []},
        headers=headers,
    )
    pid = created.json()["data"]["id"]

    got = await client.get(f"/api/v1/iam/policies/{pid}", headers=headers)
    assert got.status_code == 200

    patched = await client.patch(
        f"/api/v1/iam/policies/{pid}",
        json={"description": "updated", "statements": [{"effect": "Allow", "actions": ["*"]}]},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["description"] == "updated"

    deleted = await client.delete(f"/api/v1/iam/policies/{pid}", headers=headers)
    assert deleted.status_code == 200

    missing = await client.get(f"/api/v1/iam/policies/{pid}", headers=headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_group_crud_lifecycle(client):
    headers, _ = await _admin(client)
    policy = await get_policy_by_name_db(name="FounderAccess")
    created = await client.post(
        "/api/v1/iam/groups",
        json={"name": "CustomGroup", "policy_ids": [str(policy.id)]},
        headers=headers,
    )
    assert created.status_code == 201
    gid = created.json()["data"]["id"]

    listed = await client.get("/api/v1/iam/groups", headers=headers)
    assert any(g["name"] == "CustomGroup" for g in listed.json()["data"])

    got = await client.get(f"/api/v1/iam/groups/{gid}", headers=headers)
    assert got.status_code == 200

    patched = await client.patch(
        f"/api/v1/iam/groups/{gid}", json={"description": "team"}, headers=headers
    )
    assert patched.status_code == 200

    deleted = await client.delete(f"/api/v1/iam/groups/{gid}", headers=headers)
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_patch_managed_group_conflicts(client):
    headers, _ = await _admin(client)
    group = await get_group_by_name_db(name="Members")
    resp = await client.patch(
        f"/api/v1/iam/groups/{group.id}", json={"description": "x"}, headers=headers
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_and_get_iam_users(client):
    headers, admin_user = await _admin(client)
    listed = await client.get("/api/v1/iam/users", headers=headers)
    assert listed.status_code == 200
    assert any(u["email"] == admin_user.email for u in listed.json()["data"])

    got = await client.get(f"/api/v1/iam/users/{admin_user.id}", headers=headers)
    assert got.status_code == 200
    assert "effective" in got.json()["data"]
