"""Password reset — channel chosen by identifier SYNTAX, never account state
(non-enumerable). Fails closed in production; in dev the code goes to the log,
never the HTTP response."""

import secrets

from nawa_api.contracts.auth import ForgotPasswordInput, ResetPasswordInput
from nawa_api.contracts.common import is_email_syntax, is_phone_syntax
from nawa_api.contracts.errors import (
    ERR_EMAIL_NOT_CONFIGURED,
    ERR_INVALID_FIELDS,
    ERR_SMS_NOT_CONFIGURED,
)
from nawa_api.db.auth.revoke_all_user_refresh_tokens_db import revoke_all_user_refresh_tokens_db
from nawa_api.db.users.get_user_by_identifier_db import get_user_by_identifier_db
from nawa_api.db.users.update_user_db import update_user_db
from nawa_api.runtime.redis import get_redis
from nawa_api.runtime.settings import get_settings
from nawa_api.utils.logger import get_logger
from nawa_api.utils.password import hash_password

_CODE_TTL_SECONDS = 15 * 60


def _reset_key(identifier: str) -> str:
    return f"auth:reset:{identifier}"


async def forgot_password(body: ForgotPasswordInput) -> None:
    identifier = body.identifier
    settings = get_settings()
    is_production = settings.environment == "production"

    # Channel by syntax, never account state.
    if is_email_syntax(identifier):
        # No email channel is configured in this build.
        if is_production:
            raise ERR_EMAIL_NOT_CONFIGURED
    elif is_phone_syntax(identifier):
        if is_production:
            raise ERR_SMS_NOT_CONFIGURED
    # else: username identifier — treat as email-style, still non-enumerable.

    code = f"{secrets.randbelow(1_000_000):06d}"
    await get_redis().setex(_reset_key(identifier), _CODE_TTL_SECONDS, code)
    # Dev only: log the code, never return it in the response.
    if not is_production:
        get_logger().info("password_reset_code", identifier=identifier, code=code)


async def reset_password(body: ResetPasswordInput) -> None:
    redis = get_redis()
    stored = await redis.get(_reset_key(body.identifier))
    if stored is None or stored != body.code:
        raise ERR_INVALID_FIELDS

    user = await get_user_by_identifier_db(identifier=body.identifier)
    if user is None:
        raise ERR_INVALID_FIELDS

    await update_user_db(user_id=user.id, password_hash=hash_password(body.new_password))
    await redis.delete(_reset_key(body.identifier))
    await revoke_all_user_refresh_tokens_db(user_id=user.id)
