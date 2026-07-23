"""Shared by signup/login/refresh: resolve perms, mint the session JWT, create
the refresh token, and either queue web cookies or return a bearer TokenPair.
"""

import uuid
from datetime import UTC, datetime, timedelta

from nawa_api.contracts.auth import SessionUser, UserDto
from nawa_api.db.auth.create_refresh_token_db import create_refresh_token_db
from nawa_api.models.identity import User
from nawa_api.runtime.settings import get_settings
from nawa_api.services.iam.resolve_effective_permissions import resolve_effective_permissions
from nawa_api.utils.request_context import issue_refresh_cookie, issue_session_cookie
from nawa_api.utils.tokens import generate_opaque_token, hash_opaque_token, mint_session_jwt


async def establish_session(user: User, *, device_id: str, bearer: bool) -> dict:
    settings = get_settings()
    perms = sorted(await resolve_effective_permissions(user_id=user.id, refresh_cache=True))

    session_user = SessionUser(
        sub=str(user.id),
        full_name=user.full_name,
        language=user.language,
        perms=perms,
    )
    user_dto = UserDto(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        language=user.language,
        is_active=user.is_active,
        effective=perms,
    )

    refresh_plain = generate_opaque_token()
    await create_refresh_token_db(
        user_id=user.id,
        device_id=device_id,
        token_hash=hash_opaque_token(refresh_plain),
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.refresh_ttl_seconds),
    )

    data = user_dto.model_dump()
    if bearer:
        access_jwt = mint_session_jwt(session_user, ttl_seconds=settings.access_ttl_seconds)
        data["access_token"] = access_jwt
        data["refresh_token"] = refresh_plain
        data["expires_in"] = settings.access_ttl_seconds
    else:
        session_jwt = mint_session_jwt(session_user, ttl_seconds=settings.session_ttl_seconds)
        issue_session_cookie(session_jwt)
        issue_refresh_cookie(refresh_plain)
    return data


def new_device_id() -> str:
    return str(uuid.uuid4())
