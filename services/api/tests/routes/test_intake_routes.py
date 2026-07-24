import asyncio
import json
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
from nawa_api.db.intake.upsert_dedup_match_db import upsert_dedup_match_db
from nawa_api.db.programs.create_program_cycle_db import create_program_cycle_db
from nawa_api.db.programs.create_program_db import create_program_db
from nawa_api.db.users.create_user_db import create_user_db
from nawa_api.runtime.redis import get_redis
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


_UPLOAD_CSV = b"name,email,idea\nAmina,amina@x.io,Solar irrigation\n"
_UPLOAD_COLUMN_MAP = json.dumps(
    {"name": "applicant_name", "email": "applicant_email", "idea": "idea"}
)


@pytest.mark.asyncio
async def test_uploads_route_returns_202_with_upload_id_and_row_count(client):
    program = await create_program_db(slug="p-up1", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c-up1", name_en="C")

    headers = await _bearer(client, email="ingest1@example.com", group="Administrators")
    resp = await client.post(
        f"/api/v1/intake/cycles/{cycle.id}/uploads",
        data={"column_map": _UPLOAD_COLUMN_MAP},
        files={"file": ("batch.csv", _UPLOAD_CSV, "text/csv")},
        headers=headers,
    )
    assert resp.status_code == 202
    data = resp.json()["data"]
    assert data["row_count"] == 1
    assert uuid.UUID(data["upload_id"])


@pytest.mark.asyncio
async def test_uploads_route_requires_ingest_permission(client):
    program = await create_program_db(slug="p-up2", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c-up2", name_en="C")

    headers = await _bearer(client, email="member5@example.com", group="Members")
    resp = await client.post(
        f"/api/v1/intake/cycles/{cycle.id}/uploads",
        data={"column_map": _UPLOAD_COLUMN_MAP},
        files={"file": ("batch.csv", _UPLOAD_CSV, "text/csv")},
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_uploads_route_bad_column_map_json_returns_400(client):
    program = await create_program_db(slug="p-up3", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c-up3", name_en="C")

    headers = await _bearer(client, email="ingest2@example.com", group="Administrators")
    resp = await client.post(
        f"/api/v1/intake/cycles/{cycle.id}/uploads",
        data={"column_map": "not-json"},
        files={"file": ("batch.csv", _UPLOAD_CSV, "text/csv")},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_uploads_route_rate_limited_after_five_calls(client):
    program = await create_program_db(slug="p-up4", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c-up4", name_en="C")

    headers = await _bearer(client, email="ingest3@example.com", group="Administrators")
    for _ in range(5):
        resp = await client.post(
            f"/api/v1/intake/cycles/{cycle.id}/uploads",
            data={"column_map": _UPLOAD_COLUMN_MAP},
            files={"file": ("batch.csv", _UPLOAD_CSV, "text/csv")},
            headers=headers,
        )
        assert resp.status_code == 202
    resp = await client.post(
        f"/api/v1/intake/cycles/{cycle.id}/uploads",
        data={"column_map": _UPLOAD_COLUMN_MAP},
        files={"file": ("batch.csv", _UPLOAD_CSV, "text/csv")},
        headers=headers,
    )
    assert resp.status_code == 429
    # `@audited` schedules its write via a bare `asyncio.create_task` (fire-
    # and-forget by design). Give it a beat to finish before the next test's
    # `client` fixture truncates `users` out from under it mid-flight.
    await asyncio.sleep(0.2)


@pytest.mark.asyncio
async def test_score_route_returns_202(client):
    program = await create_program_db(slug="p-sc1", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c-sc1", name_en="C")

    headers = await _bearer(client, email="scorer1@example.com", group="Administrators")
    resp = await client.post(f"/api/v1/intake/cycles/{cycle.id}/score", headers=headers)
    assert resp.status_code == 202
    assert resp.json()["data"]["cycle_id"] == str(cycle.id)


@pytest.mark.asyncio
async def test_score_route_requires_score_permission(client):
    program = await create_program_db(slug="p-sc2", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c-sc2", name_en="C")

    headers = await _bearer(client, email="member6@example.com", group="Members")
    resp = await client.post(f"/api/v1/intake/cycles/{cycle.id}/score", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_score_route_rate_limited_after_thirty_calls(client):
    program = await create_program_db(slug="p-sc3", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c-sc3", name_en="C")

    headers = await _bearer(client, email="scorer2@example.com", group="Administrators")
    for _ in range(30):
        resp = await client.post(f"/api/v1/intake/cycles/{cycle.id}/score", headers=headers)
        assert resp.status_code == 202
    resp = await client.post(f"/api/v1/intake/cycles/{cycle.id}/score", headers=headers)
    assert resp.status_code == 429
    await asyncio.sleep(0.2)


@pytest.mark.asyncio
async def test_score_progress_route_reads_the_hash(client):
    cycle_id = uuid.uuid4()
    await get_redis().hset(
        f"jobs:intake:score:{cycle_id}:progress", mapping={"total": 10, "done": 4, "failed": 1}
    )

    headers = await _bearer(client, email="reviewer4@example.com", group="Administrators")
    resp = await client.get(f"/api/v1/intake/cycles/{cycle_id}/score/progress", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"] == {"total": 10, "done": 4, "failed": 1, "stopped_reason": None}


@pytest.mark.asyncio
async def test_upload_events_route_streams_the_upload_channel_with_a_snapshot(client, monkeypatch):
    captured = {}

    def fake_sse_response(channel, *, first_frame=None):
        from starlette.responses import PlainTextResponse

        captured["channel"] = channel
        captured["first_frame"] = first_frame
        return PlainTextResponse("ok")

    monkeypatch.setattr("nawa_api.routes.intake.sse_response", fake_sse_response)

    upload_id = uuid.uuid4()
    await get_redis().hset(
        f"jobs:intake:upload:{upload_id}:progress", mapping={"total": 5, "done": 2, "failed": 0}
    )

    headers = await _bearer(client, email="reviewer5@example.com", group="Administrators")
    resp = await client.get(f"/api/v1/intake/uploads/{upload_id}/events", headers=headers)

    assert resp.status_code == 200
    assert captured["channel"] == f"events:intake:upload:{upload_id}"
    assert json.loads(captured["first_frame"]) == {
        "type": "snapshot",
        "total": 5,
        "done": 2,
        "failed": 0,
        "stopped_reason": None,
    }


@pytest.mark.asyncio
async def test_upload_events_route_requires_review_permission(client):
    headers = await _bearer(client, email="member7@example.com", group="Members")
    resp = await client.get(f"/api/v1/intake/uploads/{uuid.uuid4()}/events", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_score_events_route_streams_the_score_channel_with_a_snapshot(client, monkeypatch):
    captured = {}

    def fake_sse_response(channel, *, first_frame=None):
        from starlette.responses import PlainTextResponse

        captured["channel"] = channel
        captured["first_frame"] = first_frame
        return PlainTextResponse("ok")

    monkeypatch.setattr("nawa_api.routes.intake.sse_response", fake_sse_response)

    cycle_id = uuid.uuid4()
    await get_redis().hset(
        f"jobs:intake:score:{cycle_id}:progress", mapping={"total": 3, "done": 3, "failed": 0}
    )

    headers = await _bearer(client, email="reviewer6@example.com", group="Administrators")
    resp = await client.get(f"/api/v1/intake/cycles/{cycle_id}/score/events", headers=headers)

    assert resp.status_code == 200
    assert captured["channel"] == f"events:intake:score:{cycle_id}"
    assert json.loads(captured["first_frame"])["done"] == 3


@pytest.mark.asyncio
async def test_resolve_dedup_match_route_confirms(client):
    program = await create_program_db(slug="p-dd1", kind="competition", name_en="P")
    cycle = await create_program_cycle_db(program_id=program.id, slug="c-dd1", name_en="C")
    a = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="A",
        applicant_email="a-dd1@x.io",
        source_language="en",
        original_answers={},
    )
    b = await create_application_db(
        cycle_id=cycle.id,
        applicant_name="B",
        applicant_email="b-dd1@x.io",
        source_language="en",
        original_answers={},
    )
    await upsert_dedup_match_db(application_id=a.id, matched_application_id=b.id, similarity=0.9)

    from nawa_api.db.intake.list_dedup_matches_db import list_dedup_matches_db

    match = (await list_dedup_matches_db(application_id=a.id))[0]

    headers = await _bearer(client, email="overrider1@example.com", group="Administrators")
    resp = await client.patch(
        f"/api/v1/intake/dedup-matches/{match.id}",
        json={"status": "confirmed"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_resolve_dedup_match_route_requires_override_permission(client):
    headers = await _bearer(client, email="member8@example.com", group="Members")
    resp = await client.patch(
        f"/api/v1/intake/dedup-matches/{uuid.uuid4()}",
        json={"status": "confirmed"},
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_resolve_dedup_match_route_rate_limited_after_sixty_calls(client):
    headers = await _bearer(client, email="overrider2@example.com", group="Administrators")
    for _ in range(60):
        resp = await client.patch(
            f"/api/v1/intake/dedup-matches/{uuid.uuid4()}",
            json={"status": "confirmed"},
            headers=headers,
        )
        assert resp.status_code == 404
    resp = await client.patch(
        f"/api/v1/intake/dedup-matches/{uuid.uuid4()}",
        json={"status": "confirmed"},
        headers=headers,
    )
    assert resp.status_code == 429
    await asyncio.sleep(0.2)
