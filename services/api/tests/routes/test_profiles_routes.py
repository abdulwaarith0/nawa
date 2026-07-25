import uuid
from datetime import UTC, datetime

import pytest

from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
from nawa_api.db.cohorts.create_cohort_member_db import create_cohort_member_db
from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.profiles.create_founder_profile_db import create_founder_profile_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.utils.password import hash_password


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
