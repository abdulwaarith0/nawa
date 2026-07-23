import time

from nawa_api.contracts.auth import SessionUser
from nawa_api.utils.tokens import (
    decode_session_jwt,
    generate_opaque_token,
    hash_opaque_token,
    mint_session_jwt,
)


def _session() -> SessionUser:
    return SessionUser(
        sub="user-1", full_name="Alice", language="en", perms=["nawa:community:read"]
    )


def test_mint_and_decode_round_trips_claims():
    token = mint_session_jwt(_session(), ttl_seconds=900)
    decoded = decode_session_jwt(token)
    assert decoded is not None
    assert decoded.sub == "user-1"
    assert decoded.full_name == "Alice"
    assert decoded.language == "en"
    assert decoded.perms == ["nawa:community:read"]


def test_decode_returns_none_for_garbage_token():
    assert decode_session_jwt("not-a-jwt") is None


def test_decode_returns_none_for_expired_token():
    token = mint_session_jwt(_session(), ttl_seconds=-1)
    time.sleep(0.01)
    assert decode_session_jwt(token) is None


def test_decode_returns_none_for_wrong_signature(monkeypatch):
    token = mint_session_jwt(_session(), ttl_seconds=900)
    # Tamper with the payload so the signature no longer verifies.
    parts = token.split(".")
    tampered = parts[0] + "." + parts[1][:-2] + "XX" + "." + parts[2]
    assert decode_session_jwt(tampered) is None


def test_opaque_token_generation_and_hashing():
    token = generate_opaque_token()
    assert isinstance(token, str)
    assert len(token) >= 32
    hashed = hash_opaque_token(token)
    assert hashed != token
    assert hash_opaque_token(token) == hashed  # deterministic (sha256)


def test_opaque_tokens_are_unique():
    assert generate_opaque_token() != generate_opaque_token()
