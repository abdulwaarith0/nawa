import pytest


@pytest.mark.asyncio
async def test_login_rate_limited_after_10_attempts(client):
    # 10 login attempts allowed in the window; the 11th → 429.
    last = None
    for _ in range(11):
        last = await client.post(
            "/api/v1/auth/login",
            json={"identifier": "nobody@example.com", "password": "whatever12"},
        )
    assert last.status_code == 429
    assert last.headers.get("retry-after") is not None
    assert last.headers.get("x-ratelimit-limit") == "10"


@pytest.mark.asyncio
async def test_rate_limit_headers_present_on_normal_request(client):
    resp = await client.get("/api/v1/site-config")
    assert resp.headers.get("x-ratelimit-limit") == "100"
    assert resp.headers.get("x-ratelimit-remaining") is not None


@pytest.mark.asyncio
async def test_bypass_flag_disables_rate_limiting(client, monkeypatch):
    async def _always_off(key, default):
        return False

    monkeypatch.setattr("nawa_api.middleware.rate_limit.get_flag", _always_off)
    last = None
    for _ in range(15):
        last = await client.post(
            "/api/v1/auth/login",
            json={"identifier": "nobody2@example.com", "password": "whatever12"},
        )
    # Never 429 (bypassed); all are the generic 401.
    assert last.status_code == 401
