import pytest


@pytest.mark.asyncio
async def test_healthz_returns_ok(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readyz_returns_ready(client):
    resp = await client.get("/readyz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_unknown_route_returns_404_envelope(client):
    resp = await client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404
    assert body["data"] is None


@pytest.mark.asyncio
async def test_metrics_exposes_histograms(client):
    # generate one request so histograms have samples
    await client.get("/api/v1/site-config")
    resp = await client.get("/api/v1/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "http_request_duration_seconds" in text
    assert "database_request_duration_seconds" in text


@pytest.mark.asyncio
async def test_request_id_is_echoed(client):
    resp = await client.get("/api/v1/site-config", headers={"x-request-id": "probe-123"})
    assert resp.headers.get("x-request-id") == "probe-123"


@pytest.mark.asyncio
async def test_auth_me_without_session_returns_401(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == 401
    assert body["message"] == "Authentication required"
