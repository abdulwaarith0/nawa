import uuid

from nawa_api.contracts.auth import UserDto
from nawa_api.contracts.errors import ERR_UNAUTHENTICATED
from nawa_api.db.users.get_user_by_id_db import get_user_by_id_db
from nawa_api.services.iam.resolve_effective_permissions import resolve_effective_permissions
from nawa_api.utils.request_context import get_session_user


async def get_me() -> dict:
    session = get_session_user()
    if session is None:
        raise ERR_UNAUTHENTICATED
    user = await get_user_by_id_db(user_id=uuid.UUID(session.sub))
    if user is None:
        raise ERR_UNAUTHENTICATED
    perms = sorted(await resolve_effective_permissions(user_id=user.id))
    return UserDto(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        language=user.language,
        is_active=user.is_active,
        effective=perms,
    ).model_dump()
