import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import RefreshToken
from nawa_api.utils.logger import get_logger


async def create_refresh_token_db(
    *,
    user_id: uuid.UUID,
    device_id: str,
    token_hash: str,
    expires_at: datetime,
    session: AsyncSession | None = None,
) -> RefreshToken | None:
    with observe_db(
        operation="write", table="refresh_tokens", method="create_refresh_token_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = RefreshToken(
                    user_id=user_id,
                    device_id=device_id,
                    token_hash=token_hash,
                    expires_at=expires_at,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_refresh_token_db", exc_info=True)
            obs.success = False
            return None
