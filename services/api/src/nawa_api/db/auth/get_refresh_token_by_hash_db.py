from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import RefreshToken
from nawa_api.utils.logger import get_logger


async def get_refresh_token_by_hash_db(
    *, token_hash: str, session: AsyncSession | None = None
) -> RefreshToken | None:
    with observe_db(
        operation="read", table="refresh_tokens", method="get_refresh_token_by_hash_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = (
                    await s.execute(
                        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
                    )
                ).scalar_one_or_none()
            obs.success = row is not None
            return row
        except Exception:
            get_logger().warning("db_error", method="get_refresh_token_by_hash_db", exc_info=True)
            obs.success = False
            return None
