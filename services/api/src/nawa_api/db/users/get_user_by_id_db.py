import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import User


async def get_user_by_id_db(
    *, user_id: uuid.UUID, session: AsyncSession | None = None
) -> User | None:
    with observe_db(operation="read", table="users", method="get_user_by_id_db") as obs:
        try:
            async with use_session(session) as s:
                row = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
            obs.success = row is not None
            return row
        except Exception:
            obs.success = False
            return None
