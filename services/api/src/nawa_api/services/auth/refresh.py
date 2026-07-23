"""Refresh rotation + theft detection (§8.3).

Reuse of a revoked token revokes the entire {user_id, device_id} chain — the
theft-detection tripwire — and is audit-logged.
"""

from datetime import UTC, datetime

from nawa_api.contracts.errors import ERR_UNAUTHENTICATED
from nawa_api.db.audit.create_audit_log_db import create_audit_log_db
from nawa_api.db.auth.get_refresh_token_by_hash_db import get_refresh_token_by_hash_db
from nawa_api.db.auth.revoke_device_chain_db import revoke_device_chain_db
from nawa_api.db.auth.revoke_refresh_token_db import revoke_refresh_token_db
from nawa_api.db.users.get_user_by_id_db import get_user_by_id_db
from nawa_api.services.auth.establish_session import establish_session
from nawa_api.utils.tokens import hash_opaque_token


async def refresh(*, token_plain: str | None, bearer: bool) -> dict:
    if not token_plain:
        raise ERR_UNAUTHENTICATED

    row = await get_refresh_token_by_hash_db(token_hash=hash_opaque_token(token_plain))
    if row is None:
        raise ERR_UNAUTHENTICATED
    if row.expires_at <= datetime.now(UTC):
        raise ERR_UNAUTHENTICATED

    if row.revoked_at is not None:
        # Reuse of a revoked token → revoke the whole device chain (tripwire).
        await revoke_device_chain_db(user_id=row.user_id, device_id=row.device_id)
        await create_audit_log_db(
            actor_id=row.user_id,
            action="auth.refresh.reuse_detected",
            target_type="user",
            target_id=row.user_id,
        )
        raise ERR_UNAUTHENTICATED

    user = await get_user_by_id_db(user_id=row.user_id)
    if user is None or not user.is_active:
        raise ERR_UNAUTHENTICATED

    await revoke_refresh_token_db(token_id=row.id)
    return await establish_session(user, device_id=row.device_id, bearer=bearer)
