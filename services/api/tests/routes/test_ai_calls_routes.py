import pytest

from nawa_api.db.ai_calls.create_ai_call_db import create_ai_call_db
from nawa_api.db.iam.add_group_member_db import add_group_member_db
from nawa_api.db.iam.get_group_by_name_db import get_group_by_name_db
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
    return {"authorization": f"Bearer {resp.json()['data']['access_token']}"}


async def _seed_call(*, task="intake.score", status="ok", provider="mock"):
    return await create_ai_call_db(
        task=task,
        provider=provider,
        model="claude-opus-4-8",
        prompt_hash="h",
        prompt_version="v1",
        status=status,
        cost_estimate=0.01,
        tokens_in=10,
        tokens_out=5,
    )


@pytest.mark.asyncio
async def test_admin_lists_ai_calls(client):
    await _seed_call(status="ok")
    await _seed_call(status="error")
    headers = await _bearer(client, email="aiadmin@example.com", group="Administrators")
    resp = await client.get("/api/v1/admin/ai-calls", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2
    assert {r["status"] for r in data} == {"ok", "error"}
    assert all("cost_estimate" in r and "prompt_hash" not in r for r in data)


@pytest.mark.asyncio
async def test_status_filter(client):
    await _seed_call(status="ok")
    await _seed_call(status="error")
    headers = await _bearer(client, email="aiadmin2@example.com", group="Administrators")
    resp = await client.get("/api/v1/admin/ai-calls?status=error", headers=headers)
    data = resp.json()["data"]
    assert [r["status"] for r in data] == ["error"]


@pytest.mark.asyncio
async def test_requires_permission(client):
    headers = await _bearer(client, email="aimember@example.com", group="Members")
    resp = await client.get("/api/v1/admin/ai-calls", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_echo_stream_emits_delta_then_done(client):
    headers = await _bearer(client, email="streamer@example.com", group="Administrators")
    lines: list[str] = []
    async with client.stream(
        "POST", "/api/v1/ai/echo-stream", json={"text": "hello"}, headers=headers
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        async for line in resp.aiter_lines():
            lines.append(line)
            if "event: done" in line or len(lines) > 100:
                break
    blob = "\n".join(lines)
    assert "event: delta" in blob
    assert "event: done" in blob


@pytest.mark.asyncio
async def test_echo_stream_requires_stream_permission(client):
    headers = await _bearer(client, email="nostream@example.com", group="Members")
    resp = await client.post("/api/v1/ai/echo-stream", json={"text": "hi"}, headers=headers)
    assert resp.status_code == 403
