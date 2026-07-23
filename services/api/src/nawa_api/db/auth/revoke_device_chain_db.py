import uuid

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import RefreshToken
from nawa_api.utils.logger import get_logger


async def revoke_device_chain_db(
    *, user_id: uuid.UUID, device_id: str, session: AsyncSession | None = None
) -> bool:
    """Revoke every live refresh token for a {user_id, device_id} — the
    theft-detection tripwire when a revoked token is replayed."""
    with observe_db(
        operation="write", table="refresh_tokens", method="revoke_device_chain_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                await s.execute(
                    update(RefreshToken)
                    .where(
                        RefreshToken.user_id == user_id,
                        RefreshToken.device_id == device_id,
                        RefreshToken.revoked_at.is_(None),
                    )
                    .values(revoked_at=func.now())
                )
            obs.success = True
            return True
        except Exception:
            get_logger().warning("db_error", method="revoke_device_chain_db", exc_info=True)
            obs.success = False
            return False
