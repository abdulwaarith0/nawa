import uuid
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import User


async def update_user_db(
    *,
    user_id: uuid.UUID,
    session: AsyncSession | None = None,
    **fields: Any,
) -> bool:
    with observe_db(operation="write", table="users", method="update_user_db") as obs:
        try:
            async with use_session(session) as s:
                result = await s.execute(update(User).where(User.id == user_id).values(**fields))
            obs.success = result.rowcount > 0
            return obs.success
        except Exception:
            obs.success = False
            return False
