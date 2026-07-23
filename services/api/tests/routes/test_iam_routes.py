import pytest

from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.iam.get_policy_by_name_db import get_policy_by_name_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.utils.password import hash_password


async def _make_user_in_group(*, email: str, group_name: str):
    user = await create_user_db(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("password123"),
        full_name=email.split("@")[0].title(),
    )
    group = await get_group_by_name_db(name=group_name)
    await add_group_member_db(group_id=group.id, user_id=user.id)
    return user


async def _bearer(client, email: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "password123"},
        headers={"x-client": "mobile", "x-device-id": f"dev-{email}"},
    )
    token = resp.json()["data"]["access_token"]
    return {"authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_member_cannot_list_policies(client):
    await _make_user_in_group(email="member1@example.com", group_name="Members")
    headers = await _bearer(client, "member1@example.com")
    resp = await client.get("/api/v1/iam/policies", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_lists_seven_builtin_policies(client):
    await _make_user_in_group(email="admin1@example.com", group_name="Administrators")
    headers = await _bearer(client, "admin1@example.com")
    resp = await client.get("/api/v1/iam/policies", headers=headers)
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()["data"]}
    assert names == {
        "AdministratorAccess",
        "ProgramManagerAccess",
        "ReviewerAccess",
        "FounderAccess",
        "MentorAccess",
        "ModeratorAccess",
        "MembersBaseline",
    }


@pytest.mark.asyncio
async def test_patch_managed_policy_conflicts(client):
    await _make_user_in_group(email="admin2@example.com", group_name="Administrators")
    headers = await _bearer(client, "admin2@example.com")
    policy = await get_policy_by_name_db(name="MembersBaseline")
    resp = await client.patch(
        f"/api/v1/iam/policies/{policy.id}",
        json={"description": "hijack"},
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_policy_then_grant_takes_effect_immediately(client):
    admin = "admin3@example.com"
    member = "member3@example.com"
    await _make_user_in_group(email=admin, group_name="Administrators")
    member_user = await _make_user_in_group(email=member, group_name="Members")
    admin_headers = await _bearer(client, admin)
    member_headers = await _bearer(client, member)

    # Member is denied the IAM console.
    before = await client.get("/api/v1/iam/policies", headers=member_headers)
    assert before.status_code == 403

    # Admin attaches AdministratorAccess directly to the member.
    admin_policy = await get_policy_by_name_db(name="AdministratorAccess")
    grant = await client.put(
        f"/api/v1/iam/users/{member_user.id}/access",
        json={"attached_policy_ids": [str(admin_policy.id)]},
        headers=admin_headers,
    )
    assert grant.status_code == 200

    # Immediately allowed — eager invalidation, no 30 s wait.
    after = await client.get("/api/v1/iam/policies", headers=member_headers)
    assert after.status_code == 200


@pytest.mark.asyncio
async def test_create_policy_returns_201_and_lists(client):
    await _make_user_in_group(email="admin4@example.com", group_name="Administrators")
    headers = await _bearer(client, "admin4@example.com")
    resp = await client.post(
        "/api/v1/iam/policies",
        json={
            "name": "DenyCommunityRead",
            "statements": [{"effect": "Deny", "actions": ["nawa:community:read"]}],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["name"] == "DenyCommunityRead"
