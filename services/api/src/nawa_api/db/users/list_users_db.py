from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import clamp_pagination, use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import User


async def list_users_db(
    *,
    limit: int | None = None,
    offset: int | None = None,
    session: AsyncSession | None = None,
) -> list[User]:
    clamped_limit, clamped_offset = clamp_pagination(limit=limit, offset=offset)
    with observe_db(operation="read", table="users", method="list_users_db") as obs:
        try:
            async with use_session(session) as s:
                rows = (
                    (
                        await s.execute(
                            select(User)
                            .order_by(User.created_at.desc())
                            .limit(clamped_limit)
                            .offset(clamped_offset)
                        )
                    )
                    .scalars()
                    .all()
                )
            obs.success = True
            return list(rows)
        except Exception:
            obs.success = False
            return []
