import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
from nawa_api.db.cohorts.create_cohort_member_db import create_cohort_member_db
from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.db import utils as db_utils
from nawa_api.models.profiles import FounderProfile
from nawa_api.services.profiles.list_profile_program_history import (
    list_profile_program_history,
)
from nawa_api.utils.password import hash_password


async def _mutate_profile(profile_id, **fields):
    """Test-only helper: some profile fields (is_public, asks, ...) have no
    kwarg on `create_founder_profile_db` because no write endpoint exists
    yet in this slice's scope, so tests set them directly through the ORM,
    against the same (monkeypatched) session_factory the app itself uses."""
    async with db_utils.session_factory() as session:
        row = (
            await session.execute(select(FounderProfile).where(FounderProfile.id == profile_id))
        ).scalar_one()
        for key, value in fields.items():
            setattr(row, key, value)
        await session.commit()


async def _bearer(client, *, email, group):
    user = await create_user_db(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("password123"),
        full_name="Tester",
    )
    grp = await get_group_by_name_db(name=group)
    await add_group_member_db(group_id=grp.id, user_id=user.id)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "password123"},
        headers={"x-client": "mobile", "x-device-id": "dev"},
    )
    return user, {"authorization": f"Bearer {resp.json()['data']['access_token']}"}


@pytest.mark.asyncio
async def test_program_history_requires_authentication(client):
    resp = await client.get("/api/v1/profiles/me/program-history")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_program_history_404s_without_a_founder_profile(client):
    _user, headers = await _bearer(client, email="nofounder@example.com", group="Founders")
    resp = await client.get("/api/v1/profiles/me/program-history", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_program_history_returns_own_cohorts(client):
    user, headers = await _bearer(client, email="withfounder@example.com", group="Founders")
    profile = await create_founder_profile_db(
        user_id=user.id, handle=f"h-{uuid.uuid4().hex[:8]}", display_name_en="F"
    )
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="accelerator", name_en="Stars"
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C"
    )
    manager = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"m{uuid.uuid4().hex[:8]}",
        password_hash="h",
        full_name="M",
    )
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=manager.id,
        starts_at=datetime(2026, 1, 1, tzinfo=UTC),
        name_en="Cohort",
    )
    await create_cohort_member_db(cohort_id=cohort.id, profile_id=profile.id)

    resp = await client.get("/api/v1/profiles/me/program-history", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["cohort_id"] == str(cohort.id)
    assert data[0]["program_name_en"] == "Stars"


@pytest.mark.asyncio
async def test_profile_by_handle_404s_on_missing_handle(client):
    _viewer, headers = await _bearer(client, email="viewer1@example.com", group="Founders")
    resp = await client.get("/api/v1/profiles/no-such-handle", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_profile_by_handle_404s_not_403_for_private_profile_seen_by_non_owner(client):
    owner = await create_user_db(
        email="private-owner@example.com",
        username="privateowner",
        password_hash="h",
        full_name="Private Owner",
    )
    profile = await create_founder_profile_db(
        user_id=owner.id, handle="private-founder", display_name_en="Private"
    )
    await _mutate_profile(profile.id, is_public=False)

    _viewer, headers = await _bearer(client, email="viewer2@example.com", group="Founders")
    resp = await client.get("/api/v1/profiles/private-founder", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_profile_by_handle_200s_for_owner_viewing_own_private_profile(client):
    owner, owner_headers = await _bearer(
        client, email="owner-view@example.com", group="Founders"
    )
    profile = await create_founder_profile_db(
        user_id=owner.id, handle="owner-private", display_name_en="Owner Private"
    )
    await _mutate_profile(profile.id, is_public=False)

    resp = await client.get("/api/v1/profiles/owner-private", headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["handle"] == "owner-private"


@pytest.mark.asyncio
async def test_profile_by_handle_200s_for_staff_viewing_private_profile(client):
    owner = await create_user_db(
        email="staff-target@example.com",
        username="stafftarget",
        password_hash="h",
        full_name="Staff Target",
    )
    profile = await create_founder_profile_db(
        user_id=owner.id, handle="staff-target-handle", display_name_en="Target"
    )
    await _mutate_profile(profile.id, is_public=False)

    _staff, staff_headers = await _bearer(
        client, email="pm@example.com", group="Program Managers"
    )
    resp = await client.get("/api/v1/profiles/staff-target-handle", headers=staff_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_profile_by_handle_200s_for_public_profile_from_any_member(client):
    owner = await create_user_db(
        email="public-owner@example.com",
        username="publicowner",
        password_hash="h",
        full_name="Public Owner",
    )
    await create_founder_profile_db(
        user_id=owner.id, handle="public-founder", display_name_en="Public Founder"
    )

    _viewer, headers = await _bearer(client, email="viewer3@example.com", group="Founders")
    resp = await client.get("/api/v1/profiles/public-founder", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["handle"] == "public-founder"


@pytest.mark.asyncio
async def test_profile_by_handle_program_history_matches_the_reused_service(client):
    owner = await create_user_db(
        email="history-owner@example.com",
        username="historyowner",
        password_hash="h",
        full_name="History Owner",
    )
    profile = await create_founder_profile_db(
        user_id=owner.id, handle="history-founder", display_name_en="History Founder"
    )
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="accelerator", name_en="Stars"
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C"
    )
    manager = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"m{uuid.uuid4().hex[:8]}",
        password_hash="h",
        full_name="M",
    )
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=manager.id,
        starts_at=datetime(2026, 1, 1, tzinfo=UTC),
        name_en="Cohort",
    )
    await create_cohort_member_db(cohort_id=cohort.id, profile_id=profile.id)

    _viewer, headers = await _bearer(client, email="viewer4@example.com", group="Founders")
    resp = await client.get("/api/v1/profiles/history-founder", headers=headers)
    assert resp.status_code == 200
    expected = await list_profile_program_history(profile_id=profile.id)
    assert resp.json()["data"]["program_history"] == expected


@pytest.mark.asyncio
async def test_profile_by_handle_filters_asks_to_active_only(client):
    owner = await create_user_db(
        email="asks-owner@example.com",
        username="asksowner",
        password_hash="h",
        full_name="Asks Owner",
    )
    profile = await create_founder_profile_db(
        user_id=owner.id, handle="asks-founder", display_name_en="Asks Founder"
    )
    await _mutate_profile(
        profile.id,
        asks=[
            {"kind": "talent", "text_en": "Need a CTO", "active": True},
            {"kind": "intro", "text_en": "Old ask", "active": False},
        ],
    )

    _viewer, headers = await _bearer(client, email="viewer5@example.com", group="Founders")
    resp = await client.get("/api/v1/profiles/asks-founder", headers=headers)
    assert resp.status_code == 200
    asks = resp.json()["data"]["asks"]
    assert len(asks) == 1
    assert asks[0]["text_en"] == "Need a CTO"
