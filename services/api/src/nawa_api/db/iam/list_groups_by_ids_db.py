import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import IamGroup
from nawa_api.utils.logger import get_logger


async def list_groups_by_ids_db(
    *, group_ids: list[uuid.UUID], session: AsyncSession | None = None
) -> list[IamGroup]:
    if not group_ids:
        return []
    with observe_db(operation="read", table="iam_groups", method="list_groups_by_ids_db") as obs:
        try:
            async with use_session(session) as s:
                rows = (
                    (await s.execute(select(IamGroup).where(IamGroup.id.in_(group_ids))))
                    .scalars()
                    .all()
                )
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_groups_by_ids_db", exc_info=True)
            obs.success = False
            return []
