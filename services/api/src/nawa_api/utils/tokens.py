"""JWT session tokens (HS256) + opaque refresh tokens (SHA-256 hashed at rest)."""

import hashlib
import secrets
import time

import jwt

from nawa_api.contracts.auth import SessionUser
from nawa_api.runtime.settings import get_settings

_ALGORITHM = "HS256"


def mint_session_jwt(session: SessionUser, *, ttl_seconds: int) -> str:
    now = int(time.time())
    claims = {
        "sub": session.sub,
        "full_name": session.full_name,
        "language": session.language,
        "perms": session.perms,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(claims, get_settings().jwt_secret, algorithm=_ALGORITHM)


def decode_session_jwt(token: str) -> SessionUser | None:
    try:
        claims = jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
    try:
        return SessionUser(
            sub=claims["sub"],
            full_name=claims["full_name"],
            language=claims["language"],
            perms=claims.get("perms", []),
        )
    except (KeyError, TypeError):
        return None


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
