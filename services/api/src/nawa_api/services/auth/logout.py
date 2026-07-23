from nawa_api.db.auth.get_refresh_token_by_hash_db import get_refresh_token_by_hash_db
from nawa_api.db.auth.revoke_device_chain_db import revoke_device_chain_db
from nawa_api.utils.request_context import revoke_session_cookie
from nawa_api.utils.tokens import hash_opaque_token


async def logout(*, refresh_token_plain: str | None) -> None:
    """Revoke the presented device's refresh chain and queue cookie revocations.
    Always succeeds (idempotent)."""
    if refresh_token_plain:
        row = await get_refresh_token_by_hash_db(token_hash=hash_opaque_token(refresh_token_plain))
        if row is not None:
            await revoke_device_chain_db(user_id=row.user_id, device_id=row.device_id)
    revoke_session_cookie()
