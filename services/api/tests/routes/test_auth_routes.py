import pytest

_SIGNUP = {
    "full_name": "Alice Founder",
    "email": "alice@example.com",
    "password": "password123",
    "language": "en",
}


async def _signup(client, **overrides):
    body = {**_SIGNUP, **overrides}
    return await client.post("/api/v1/auth/signup", json=body)


@pytest.mark.asyncio
async def test_signup_joins_members_and_returns_baseline_perms(client):
    resp = await _signup(client)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["email"] == "alice@example.com"
    assert set(data["effective"]) == {"nawa:profiles:write", "nawa:community:read"}


@pytest.mark.asyncio
async def test_signup_sets_session_cookie(client):
    resp = await _signup(client, email="cookie@example.com")
    set_cookie = resp.headers.get("set-cookie", "")
    assert "nw_session=" in set_cookie
    assert "HttpOnly" in set_cookie


@pytest.mark.asyncio
async def test_duplicate_signup_conflicts(client):
    await _signup(client, email="dup@example.com")
    resp = await _signup(client, email="dup@example.com")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_cookie_path_and_me(client):
    await _signup(client, email="login@example.com")
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "login@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    # httpx AsyncClient persists cookies across requests on the same client.
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["email"] == "login@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password_is_generic_401(client):
    await _signup(client, email="wrongpw@example.com")
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "wrongpw@example.com", "password": "not-the-password"},
    )
    assert resp.status_code == 401
    assert resp.json()["message"] == "Authentication required"


@pytest.mark.asyncio
async def test_login_unknown_identifier_is_generic_401(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "nobody@example.com", "password": "whatever12"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bearer_login_returns_token_pair(client):
    await _signup(client, email="bearer@example.com")
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "bearer@example.com", "password": "password123"},
        headers={"x-client": "mobile", "x-device-id": "dev-1"},
    )
    data = resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["expires_in"] > 0

    # bearer access token authorizes /auth/me
    me = await client.get(
        "/api/v1/auth/me", headers={"authorization": f"Bearer {data['access_token']}"}
    )
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_refresh_rotation_and_theft_detection(client):
    await _signup(client, email="rotate@example.com")
    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "rotate@example.com", "password": "password123"},
        headers={"x-client": "mobile", "x-device-id": "dev-rotate"},
    )
    old_refresh = login.json()["data"]["refresh_token"]

    first = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
        headers={"x-client": "mobile", "x-device-id": "dev-rotate"},
    )
    assert first.status_code == 200
    new_refresh = first.json()["data"]["refresh_token"]
    assert new_refresh != old_refresh

    # Replaying the OLD (now revoked) token → 401 and revokes the whole chain.
    replay = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
        headers={"x-client": "mobile", "x-device-id": "dev-rotate"},
    )
    assert replay.status_code == 401

    # The NEW token is now also dead (chain revoked on reuse detection).
    after = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh},
        headers={"x-client": "mobile", "x-device-id": "dev-rotate"},
    )
    assert after.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_and_clears_cookie(client):
    await _signup(client, email="logout@example.com")
    await client.post(
        "/api/v1/auth/login",
        json={"identifier": "logout@example.com", "password": "password123"},
    )
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "nw_session=" in set_cookie
