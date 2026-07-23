import uuid

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import RefreshToken
from nawa_api.utils.logger import get_logger


async def revoke_refresh_token_db(
    *,
    token_id: uuid.UUID,
    replaced_by_id: uuid.UUID | None = None,
    session: AsyncSession | None = None,
) -> bool:
    with observe_db(
        operation="write", table="refresh_tokens", method="revoke_refresh_token_db"
    ) as obs:
        try:
            values = {"revoked_at": func.now()}
            if replaced_by_id is not None:
                values["replaced_by_id"] = replaced_by_id
            async with use_session(session) as s:
                result = await s.execute(
                    update(RefreshToken)
                    .where(RefreshToken.id == token_id, RefreshToken.revoked_at.is_(None))
                    .values(**values)
                )
            obs.success = result.rowcount > 0
            return obs.success
        except Exception:
            get_logger().warning("db_error", method="revoke_refresh_token_db", exc_info=True)
            obs.success = False
            return False
