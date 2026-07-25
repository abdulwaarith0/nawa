import uuid
from datetime import UTC, date, datetime

import pytest

from nawa_api.db.cohorts.create_cohort_db import create_cohort_db
from nawa_api.db.cohorts.create_cohort_member_db import create_cohort_member_db
from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
from nawa_api.db.journey.create_milestone_db import create_milestone_db
from nawa_api.db.journey.create_milestone_progress_db import create_milestone_progress_db
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


async def _cohort_with_template(*, sequence=1, due_offset_days=7, starts_at=None):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="accelerator", name_en="P"
    )
    cycle = await create_program_cycle_db(
        program_id=program.id, slug=f"c-{uuid.uuid4().hex[:8]}", name_en="C"
    )
    manager = await create_user_db(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        username=f"m{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        full_name="Manager",
    )
    cohort = await create_cohort_db(
        cycle_id=cycle.id,
        program_manager_user_id=manager.id,
        starts_at=starts_at or datetime(2026, 1, 1, tzinfo=UTC),
        name_en="Cohort",
    )
    await create_milestone_db(
        program_id=program.id,
        scope="template",
        sequence=sequence,
        title_en="Kickoff",
        due_offset_days=due_offset_days,
    )
    return program, cohort


async def _founder_member(client, *, cohort_id, email=None):
    email = email or f"{uuid.uuid4().hex[:8]}@example.com"
    founder_user, headers = await _bearer(client, email=email, group="Founders")
    profile = await create_founder_profile_db(
        user_id=founder_user.id, handle=f"h-{uuid.uuid4().hex[:8]}", display_name_en="Founder"
    )
    member = await create_cohort_member_db(cohort_id=cohort_id, profile_id=profile.id)
    return founder_user, profile, member, headers


@pytest.mark.asyncio
async def test_founder_cannot_instantiate_milestones(client):
    _program, cohort = await _cohort_with_template()
    _user, headers = await _bearer(client, email="f1@example.com", group="Founders")

    resp = await client.post(
        f"/api/v1/journey/cohorts/{cohort.id}/milestones/instantiate", headers=headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_manager_instantiates_and_board_shows_grid(client):
    _program, cohort = await _cohort_with_template()
    _user, headers = await _bearer(client, email="m1@example.com", group="Program Managers")
    await _founder_member(client, cohort_id=cohort.id)

    resp = await client.post(
        f"/api/v1/journey/cohorts/{cohort.id}/milestones/instantiate", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == {"milestones_created": 1, "progress_created": 1}

    board = await client.get(f"/api/v1/journey/cohorts/{cohort.id}/board", headers=headers)
    assert board.status_code == 200
    data = board.json()["data"]
    assert len(data["milestones"]) == 1
    assert len(data["members"]) == 1
    assert len(data["cells"]) == 1


@pytest.mark.asyncio
async def test_instantiate_is_idempotent_over_http(client):
    _program, cohort = await _cohort_with_template()
    _user, headers = await _bearer(client, email="m2@example.com", group="Program Managers")
    await _founder_member(client, cohort_id=cohort.id)

    first = await client.post(
        f"/api/v1/journey/cohorts/{cohort.id}/milestones/instantiate", headers=headers
    )
    second = await client.post(
        f"/api/v1/journey/cohorts/{cohort.id}/milestones/instantiate", headers=headers
    )
    assert first.json()["data"] == {"milestones_created": 1, "progress_created": 1}
    assert second.json()["data"] == {"milestones_created": 0, "progress_created": 0}


@pytest.mark.asyncio
async def test_milestone_template_crud_requires_manage_permission(client):
    program = await create_program_db(
        slug=f"p-{uuid.uuid4().hex[:8]}", kind="accelerator", name_en="P"
    )
    _user, headers = await _bearer(client, email="m3@example.com", group="Program Managers")

    create_resp = await client.post(
        f"/api/v1/journey/programs/{program.id}/milestone-templates",
        json={"sequence": 1, "title_en": "Kickoff", "due_offset_days": 7},
        headers=headers,
    )
    assert create_resp.status_code == 201
    template_id = create_resp.json()["data"]["id"]

    list_resp = await client.get(
        f"/api/v1/journey/programs/{program.id}/milestone-templates", headers=headers
    )
    assert len(list_resp.json()["data"]) == 1

    patch_resp = await client.patch(
        f"/api/v1/journey/milestone-templates/{template_id}",
        json={"title_en": "Renamed"},
        headers=headers,
    )
    assert patch_resp.json()["data"]["title_en"] == "Renamed"

    delete_resp = await client.delete(
        f"/api/v1/journey/milestone-templates/{template_id}", headers=headers
    )
    assert delete_resp.status_code == 200
    list_after = await client.get(
        f"/api/v1/journey/programs/{program.id}/milestone-templates", headers=headers
    )
    assert list_after.json()["data"] == []


@pytest.mark.asyncio
async def test_founder_status_done_is_rejected_with_400(client):
    _program, cohort = await _cohort_with_template()
    _mgr, mgr_headers = await _bearer(client, email="m4@example.com", group="Program Managers")
    _founder_user, _profile, member, founder_headers = await _founder_member(
        client, cohort_id=cohort.id
    )
    await client.post(
        f"/api/v1/journey/cohorts/{cohort.id}/milestones/instantiate", headers=mgr_headers
    )
    board = (
        await client.get(f"/api/v1/journey/cohorts/{cohort.id}/board", headers=mgr_headers)
    ).json()["data"]
    progress_id = next(
        c["progress_id"] for c in board["cells"] if c["cohort_member_id"] == str(member.id)
    )

    bad = await client.patch(
        f"/api/v1/journey/progress/{progress_id}",
        json={"status": "done"},
        headers=founder_headers,
    )
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_founder_owns_own_progress_but_not_others(client):
    _program, cohort = await _cohort_with_template()
    _mgr, mgr_headers = await _bearer(client, email="m6@example.com", group="Program Managers")
    _fu1, _p1, member, founder_headers = await _founder_member(client, cohort_id=cohort.id)
    _fu2, _p2, other_member, _h2 = await _founder_member(client, cohort_id=cohort.id)
    await client.post(
        f"/api/v1/journey/cohorts/{cohort.id}/milestones/instantiate", headers=mgr_headers
    )
    board = (
        await client.get(f"/api/v1/journey/cohorts/{cohort.id}/board", headers=mgr_headers)
    ).json()["data"]
    my_progress_id = next(
        c["progress_id"] for c in board["cells"] if c["cohort_member_id"] == str(member.id)
    )
    other_progress_id = next(
        c["progress_id"]
        for c in board["cells"]
        if c["cohort_member_id"] == str(other_member.id)
    )

    ok_resp = await client.patch(
        f"/api/v1/journey/progress/{my_progress_id}",
        json={"status": "in_progress"},
        headers=founder_headers,
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["data"]["status"] == "in_progress"

    foreign_resp = await client.patch(
        f"/api/v1/journey/progress/{other_progress_id}",
        json={"status": "in_progress"},
        headers=founder_headers,
    )
    assert foreign_resp.status_code == 404


@pytest.mark.asyncio
async def test_my_timeline_route_returns_own_milestones(client):
    _program, cohort = await _cohort_with_template()
    _mgr, mgr_headers = await _bearer(client, email="m7@example.com", group="Program Managers")
    _fu, _profile, _member, founder_headers = await _founder_member(client, cohort_id=cohort.id)
    await client.post(
        f"/api/v1/journey/cohorts/{cohort.id}/milestones/instantiate", headers=mgr_headers
    )

    resp = await client.get(
        "/api/v1/journey/me/timeline",
        params={"cohort_id": str(cohort.id)},
        headers=founder_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


@pytest.mark.asyncio
async def test_manager_review_requires_note_for_blocked(client):
    _program, cohort = await _cohort_with_template()
    _mgr, mgr_headers = await _bearer(client, email="m8@example.com", group="Program Managers")
    _fu, _profile, member, _fh = await _founder_member(client, cohort_id=cohort.id)
    await client.post(
        f"/api/v1/journey/cohorts/{cohort.id}/milestones/instantiate", headers=mgr_headers
    )
    board = (
        await client.get(f"/api/v1/journey/cohorts/{cohort.id}/board", headers=mgr_headers)
    ).json()["data"]
    progress_id = next(
        c["progress_id"] for c in board["cells"] if c["cohort_member_id"] == str(member.id)
    )

    no_note = await client.patch(
        f"/api/v1/journey/progress/{progress_id}/review",
        json={"status": "blocked"},
        headers=mgr_headers,
    )
    assert no_note.status_code == 400

    with_note = await client.patch(
        f"/api/v1/journey/progress/{progress_id}/review",
        json={"status": "blocked", "note_en": "Missing evidence."},
        headers=mgr_headers,
    )
    assert with_note.status_code == 200
    assert with_note.json()["data"]["status"] == "blocked"


@pytest.mark.asyncio
async def test_founder_cannot_hit_manager_review_route(client):
    _program, cohort = await _cohort_with_template()
    _mgr, mgr_headers = await _bearer(client, email="m9@example.com", group="Program Managers")
    _fu, _profile, member, founder_headers = await _founder_member(client, cohort_id=cohort.id)
    await client.post(
        f"/api/v1/journey/cohorts/{cohort.id}/milestones/instantiate", headers=mgr_headers
    )
    board = (
        await client.get(f"/api/v1/journey/cohorts/{cohort.id}/board", headers=mgr_headers)
    ).json()["data"]
    progress_id = next(
        c["progress_id"] for c in board["cells"] if c["cohort_member_id"] == str(member.id)
    )

    resp = await client.patch(
        f"/api/v1/journey/progress/{progress_id}/review",
        json={"status": "done"},
        headers=founder_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_cohort_milestones_route(client):
    _program, cohort = await _cohort_with_template()
    _mgr, mgr_headers = await _bearer(client, email="m14@example.com", group="Program Managers")
    await client.post(
        f"/api/v1/journey/cohorts/{cohort.id}/milestones/instantiate", headers=mgr_headers
    )

    resp = await client.get(
        f"/api/v1/journey/cohorts/{cohort.id}/milestones", headers=mgr_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


@pytest.mark.asyncio
async def test_update_cohort_milestone_route(client):
    _program, cohort = await _cohort_with_template()
    _mgr, mgr_headers = await _bearer(client, email="m15@example.com", group="Program Managers")
    await client.post(
        f"/api/v1/journey/cohorts/{cohort.id}/milestones/instantiate", headers=mgr_headers
    )
    milestones = (
        await client.get(f"/api/v1/journey/cohorts/{cohort.id}/milestones", headers=mgr_headers)
    ).json()["data"]

    resp = await client.patch(
        f"/api/v1/journey/milestones/{milestones[0]['id']}",
        json={"title_en": "Renamed cohort milestone"},
        headers=mgr_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["title_en"] == "Renamed cohort milestone"


@pytest.mark.asyncio
async def test_my_timeline_404s_when_caller_has_no_founder_profile(client):
    _user, headers = await _bearer(client, email="f13@example.com", group="Founders")

    resp = await client.get(
        "/api/v1/journey/me/timeline", params={"cohort_id": str(uuid.uuid4())}, headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_at_risk_route_lists_blocked(client):
    program, cohort = await _cohort_with_template()
    _mgr, mgr_headers = await _bearer(client, email="m10@example.com", group="Program Managers")
    _fu, profile, member, _fh = await _founder_member(client, cohort_id=cohort.id)
    milestone = await create_milestone_db(
        program_id=program.id,
        cohort_id=cohort.id,
        scope="cohort",
        sequence=1,
        title_en="M",
        due_date=date(2099, 1, 1),
    )
    await create_milestone_progress_db(
        milestone_id=milestone.id,
        cohort_member_id=member.id,
        founder_profile_id=profile.id,
        status="blocked",
    )

    resp = await client.get(f"/api/v1/journey/cohorts/{cohort.id}/at-risk", headers=mgr_headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1
    assert resp.json()["data"][0]["status"] == "blocked"


def _fake_sse_response(monkeypatch, captured):
    def fake(channel, *, first_frame=None):
        from starlette.responses import PlainTextResponse

        captured["channel"] = channel
        return PlainTextResponse("ok")

    monkeypatch.setattr("nawa_api.routes.journey.sse_response", fake)


@pytest.mark.asyncio
async def test_events_route_visible_to_manager(client, monkeypatch):
    _program, cohort = await _cohort_with_template()
    _mgr, mgr_headers = await _bearer(client, email="m11@example.com", group="Program Managers")
    captured = {}
    _fake_sse_response(monkeypatch, captured)

    resp = await client.get(f"/api/v1/journey/cohorts/{cohort.id}/events", headers=mgr_headers)
    assert resp.status_code == 200
    assert captured["channel"] == f"events:journey:{cohort.id}"


@pytest.mark.asyncio
async def test_events_route_visible_to_own_member(client, monkeypatch):
    _program, cohort = await _cohort_with_template()
    _fu, _profile, _member, founder_headers = await _founder_member(client, cohort_id=cohort.id)
    captured = {}
    _fake_sse_response(monkeypatch, captured)

    resp = await client.get(
        f"/api/v1/journey/cohorts/{cohort.id}/events", headers=founder_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_events_route_hidden_from_non_member_founder(client, monkeypatch):
    _program, cohort = await _cohort_with_template()
    _fu, headers = await _bearer(client, email="f12@example.com", group="Founders")
    captured = {}
    _fake_sse_response(monkeypatch, captured)

    resp = await client.get(f"/api/v1/journey/cohorts/{cohort.id}/events", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_events_route_missing_cohort_is_404(client, monkeypatch):
    _user, headers = await _bearer(client, email="m13@example.com", group="Program Managers")
    captured = {}
    _fake_sse_response(monkeypatch, captured)

    resp = await client.get(f"/api/v1/journey/cohorts/{uuid.uuid4()}/events", headers=headers)
    assert resp.status_code == 404
