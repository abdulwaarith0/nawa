import uuid

import pytest

from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.intake.create_application_db import create_application_db
from nawa_api.db.intake.create_rubric_db import create_rubric_db
from nawa_api.db.intake.create_scorecard_db import create_scorecard_db
from nawa_api.db.intake.update_application_scoring_db import update_application_scoring_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.utils.password import hash_password

_CRITERIA = [{"key": "novelty", "weight": 1.0, "scale_max": 10}]


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
    return {"authorization": f"Bearer {resp.json()['data']['access_token']}"}


async def _scored_application(*, cycle_id, rubric_id, total_score=72.0):
    app = await create_application_db(
        cycle_id=cycle_id,
        applicant_name="Amina",
        applicant_email=f"{uuid.uuid4().hex[:8]}@x.io",
        source_language="en",
        original_answers={"idea": "great idea"},
    )
    await update_application_scoring_db(application_id=app.id, total_score=total_score)
    await create_scorecard_db(
        application_id=app.id,
        rubric_id=rubric_id,
        rubric_version=1,
        prompt_version="v2",
        source="ai",
        total_score=total_score,
    )
    return app


@pytest.mark.asyncio
async def test_shortlist_route_returns_ranked_rows(client):
    program = await create_program_db(slug="p1", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c1", name_en="C")
    rubric = await create_rubric_db(
        program_id=program.id, version=1, criteria=_CRITERIA, name_en="R", status="active"
    )
    await _scored_application(cycle_id=cycle.id, rubric_id=rubric.id, total_score=42.0)

    headers = await _bearer(client, email="reviewer@example.com", group="Administrators")
    resp = await client.get(f"/api/v1/intake/cycles/{cycle.id}/shortlist", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["total_score"] == 42.0
    assert data[0]["rank"] == 1


@pytest.mark.asyncio
async def test_shortlist_route_requires_review_permission(client):
    program = await create_program_db(slug="p2", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c2", name_en="C")

    headers = await _bearer(client, email="member1@example.com", group="Members")
    resp = await client.get(f"/api/v1/intake/cycles/{cycle.id}/shortlist", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_scorecard_route_returns_full_detail(client):
    program = await create_program_db(slug="p3", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c3", name_en="C")
    rubric = await create_rubric_db(
        program_id=program.id, version=1, criteria=_CRITERIA, name_en="R", status="active"
    )
    app = await _scored_application(cycle_id=cycle.id, rubric_id=rubric.id, total_score=88.0)

    headers = await _bearer(client, email="reviewer2@example.com", group="Administrators")
    resp = await client.get(f"/api/v1/intake/applications/{app.id}/scorecard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["application"]["id"] == str(app.id)
    assert data["scorecard"]["total_score"] == 88.0


@pytest.mark.asyncio
async def test_scorecard_route_missing_application_returns_404(client):
    headers = await _bearer(client, email="reviewer3@example.com", group="Administrators")
    resp = await client.get(
        f"/api/v1/intake/applications/{uuid.uuid4()}/scorecard", headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_scorecard_route_requires_review_permission(client):
    headers = await _bearer(client, email="member2@example.com", group="Members")
    resp = await client.get(
        f"/api/v1/intake/applications/{uuid.uuid4()}/scorecard", headers=headers
    )
    assert resp.status_code == 403
