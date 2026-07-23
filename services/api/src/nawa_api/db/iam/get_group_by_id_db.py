import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import IamGroup
from nawa_api.utils.logger import get_logger


async def get_group_by_id_db(
    *, group_id: uuid.UUID, session: AsyncSession | None = None
) -> IamGroup | None:
    with observe_db(operation="read", table="iam_groups", method="get_group_by_id_db") as obs:
        try:
            async with use_session(session) as s:
                row = (
                    await s.execute(select(IamGroup).where(IamGroup.id == group_id))
                ).scalar_one_or_none()
            obs.success = row is not None
            return row
        except Exception:
            get_logger().warning("db_error", method="get_group_by_id_db", exc_info=True)
            obs.success = False
            return None
