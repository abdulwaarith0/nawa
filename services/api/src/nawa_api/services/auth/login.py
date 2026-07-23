from nawa_api.contracts.auth import LoginInput
from nawa_api.contracts.errors import ERR_UNAUTHENTICATED
from nawa_api.db.users.get_user_by_identifier_db import get_user_by_identifier_db
from nawa_api.services.auth.establish_session import establish_session, new_device_id
from nawa_api.utils.password import verify_password


async def login(body: LoginInput, *, bearer: bool, device_id: str | None = None) -> dict:
    """Content-sniffed identifier. All failures — unknown identifier, wrong
    password, deactivated account — return the same generic 401 (non-enumerable)."""
    user = await get_user_by_identifier_db(identifier=body.identifier)
    if user is None:
        raise ERR_UNAUTHENTICATED
    if not verify_password(body.password, user.password_hash):
        raise ERR_UNAUTHENTICATED
    if not user.is_active:
        raise ERR_UNAUTHENTICATED

    return await establish_session(user, device_id=device_id or new_device_id(), bearer=bearer)
