import uuid
from datetime import UTC, datetime

import pytest

from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
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
async def test_cycles_route_returns_program_name(client):
    program = await create_program_db(slug="p-cyc1", kind="competition", name_en="P Cyc")
    cycle = await create_program_cycle_db(
        program_id=program.id, slug="c-cyc1", name_en="Cyc 1", status="active"
    )

    headers = await _bearer(client, email="picker1@example.com", group="Administrators")
    resp = await client.get("/api/v1/intake/cycles", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    match = next(item for item in data if item["id"] == str(cycle.id))
    assert match["program_name_en"] == "P Cyc"


@pytest.mark.asyncio
async def test_cycles_route_filters_by_status(client):
    program = await create_program_db(slug="p-cyc2", kind="competition", name_en="P")
    await create_program_cycle_db(
        program_id=program.id, slug="c-cyc2-draft", name_en="Draft", status="draft"
    )
    active = await create_program_cycle_db(
        program_id=program.id, slug="c-cyc2-active", name_en="Active", status="active"
    )

    headers = await _bearer(client, email="picker2@example.com", group="Administrators")
    resp = await client.get("/api/v1/intake/cycles", params={"status": "active"}, headers=headers)
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()["data"]}
    assert str(active.id) in ids


@pytest.mark.asyncio
async def test_cycles_route_requires_review_permission(client):
    headers = await _bearer(client, email="member2@example.com", group="Members")
    resp = await client.get("/api/v1/intake/cycles", headers=headers)
    assert resp.status_code == 403


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


@pytest.mark.asyncio
async def test_decision_route_creates_a_decision_matching_the_ai_band(client):
    program = await create_program_db(slug="p4", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c4", name_en="C")
    rubric = await create_rubric_db(
        program_id=program.id, version=1, criteria=_CRITERIA, name_en="R", status="active"
    )
    # Sole scored applicant, default capacity (20/20) -> AI band is "shortlist".
    app = await _scored_application(cycle_id=cycle.id, rubric_id=rubric.id, total_score=80.0)

    headers = await _bearer(client, email="decider@example.com", group="Administrators")
    resp = await client.post(
        f"/api/v1/intake/applications/{app.id}/decision",
        json={"decision": "shortlist"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "shortlisted"
    assert data["overridden"] is False


@pytest.mark.asyncio
async def test_decision_route_requires_reason_when_overriding_the_ai_band(client):
    program = await create_program_db(slug="p5", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c5", name_en="C")
    rubric = await create_rubric_db(
        program_id=program.id, version=1, criteria=_CRITERIA, name_en="R", status="active"
    )
    app = await _scored_application(cycle_id=cycle.id, rubric_id=rubric.id, total_score=80.0)

    headers = await _bearer(client, email="decider2@example.com", group="Administrators")
    resp = await client.post(
        f"/api/v1/intake/applications/{app.id}/decision",
        json={"decision": "reject"},  # diverges from the "shortlist" AI band
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_decision_route_requires_override_permission(client):
    headers = await _bearer(client, email="member3@example.com", group="Members")
    resp = await client.post(
        f"/api/v1/intake/applications/{uuid.uuid4()}/decision",
        json={"decision": "shortlist"},
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_decision_route_override_with_reason_succeeds(client):
    program = await create_program_db(slug="p6", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c6", name_en="C")
    rubric = await create_rubric_db(
        program_id=program.id, version=1, criteria=_CRITERIA, name_en="R", status="active"
    )
    app = await _scored_application(cycle_id=cycle.id, rubric_id=rubric.id, total_score=80.0)

    headers = await _bearer(client, email="decider3@example.com", group="Administrators")
    resp = await client.post(
        f"/api/v1/intake/applications/{app.id}/decision",
        json={"decision": "reject", "reason": "Idea already covered elsewhere."},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["overridden"] is True
    assert data["status"] == "decided"


@pytest.mark.asyncio
async def test_decision_route_accept_creates_cohort_membership(client):
    program = await create_program_db(slug="p7", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c7", name_en="C")
    rubric = await create_rubric_db(
        program_id=program.id, version=1, criteria=_CRITERIA, name_en="R", status="active"
    )
    app = await _scored_application(cycle_id=cycle.id, rubric_id=rubric.id, total_score=80.0)

    manager = await create_user_db(
        email="manager@example.com",
        username="manager",
        password_hash=hash_password("password123"),
        full_name="Manager",
    )
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=manager.id,
        starts_at=datetime.now(UTC),
        name_en="Cohort",
    )

    headers = await _bearer(client, email="decider4@example.com", group="Administrators")
    resp = await client.post(
        f"/api/v1/intake/applications/{app.id}/decision",
        json={"decision": "accept", "cohort_id": str(cohort.id)},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["decision"] == "accept"
    assert data["profile_id"] is not None


@pytest.mark.asyncio
async def test_export_route_returns_a_presigned_url(client):
    program = await create_program_db(slug="p8", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c8", name_en="C")
    rubric = await create_rubric_db(
        program_id=program.id, version=1, criteria=_CRITERIA, name_en="R", status="active"
    )
    app = await _scored_application(cycle_id=cycle.id, rubric_id=rubric.id, total_score=80.0)

    headers = await _bearer(client, email="exporter@example.com", group="Administrators")
    decide_resp = await client.post(
        f"/api/v1/intake/applications/{app.id}/decision",
        json={"decision": "shortlist"},
        headers=headers,
    )
    assert decide_resp.status_code == 200

    resp = await client.get(f"/api/v1/intake/cycles/{cycle.id}/export", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["row_count"] == 1
    assert data["url"] is not None


@pytest.mark.asyncio
async def test_export_route_requires_export_permission(client):
    headers = await _bearer(client, email="member4@example.com", group="Members")
    resp = await client.get(
        f"/api/v1/intake/cycles/{uuid.uuid4()}/export", headers=headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_export_route_missing_cycle_returns_404(client):
    headers = await _bearer(client, email="exporter2@example.com", group="Administrators")
    resp = await client.get(
        f"/api/v1/intake/cycles/{uuid.uuid4()}/export", headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_route_rate_limited_after_five_calls(client):
    program = await create_program_db(slug="p9", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c9", name_en="C")

    headers = await _bearer(client, email="exporter3@example.com", group="Administrators")
    for _ in range(5):
        resp = await client.get(f"/api/v1/intake/cycles/{cycle.id}/export", headers=headers)
        assert resp.status_code == 200
    resp = await client.get(f"/api/v1/intake/cycles/{cycle.id}/export", headers=headers)
    assert resp.status_code == 429
