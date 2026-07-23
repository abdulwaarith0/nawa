from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import clamp_pagination, use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import IamGroup
from nawa_api.utils.logger import get_logger


async def list_groups_db(
    *,
    limit: int | None = None,
    offset: int | None = None,
    session: AsyncSession | None = None,
) -> list[IamGroup]:
    clamped_limit, clamped_offset = clamp_pagination(limit=limit, offset=offset)
    with observe_db(operation="read", table="iam_groups", method="list_groups_db") as obs:
        try:
            stmt = (
                select(IamGroup).order_by(IamGroup.name).limit(clamped_limit).offset(clamped_offset)
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_groups_db", exc_info=True)
            obs.success = False
            return []
