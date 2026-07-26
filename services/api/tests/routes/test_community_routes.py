import pytest

from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.utils.password import hash_password


async def _bearer(client, *, email, group=None):
    user = await create_user_db(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("password123"),
        full_name="Tester",
    )
    if group:
        grp = await get_group_by_name_db(name=group)
        await add_group_member_db(group_id=grp.id, user_id=user.id)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "password123"},
        headers={"x-client": "mobile", "x-device-id": "dev"},
    )
    return user, {"authorization": f"Bearer {resp.json()['data']['access_token']}"}


@pytest.mark.asyncio
async def test_directory_requires_authentication(client):
    resp = await client.get("/api/v1/community/directory")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_directory_requires_community_read_permission(client):
    # A user in no group has no permissions at all -> 403.
    _user, headers = await _bearer(client, email="noperm@example.com")
    resp = await client.get("/api/v1/community/directory", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_directory_lists_visible_profiles_and_round_trips_filters(client):
    _viewer, headers = await _bearer(client, email="viewer@example.com", group="Founders")

    owner = await create_user_db(
        email="visible@example.com",
        username="visible",
        password_hash="h",
        full_name="Visible Founder",
    )
    await create_founder_profile_db(
        user_id=owner.id,
        handle="visible-founder",
        display_name_en="Visible Founder",
        sector="agtech",
        country="QA",
        stage="pilot",
        skills=["cad"],
        domains=["agtech"],
    )

    resp = await client.get("/api/v1/community/directory", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert any(row["handle"] == "visible-founder" for row in data)
    row = next(r for r in data if r["handle"] == "visible-founder")
    assert row["sector"] == "agtech"
    assert "bio_en" not in row  # light payload, no bio
    assert "embedding" not in row

    resp2 = await client.get(
        "/api/v1/community/directory",
        params={"sector": "agtech", "country": "QA", "stage": "pilot", "skills": ["cad"]},
        headers=headers,
    )
    assert resp2.status_code == 200
    assert any(r["handle"] == "visible-founder" for r in resp2.json()["data"])

    resp3 = await client.get(
        "/api/v1/community/directory", params={"sector": "fintech"}, headers=headers
    )
    assert resp3.status_code == 200
    assert all(r["handle"] != "visible-founder" for r in resp3.json()["data"])
