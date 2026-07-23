import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import IamGroup
from nawa_api.utils.logger import get_logger


async def delete_group_db(*, group_id: uuid.UUID, session: AsyncSession | None = None) -> bool:
    with observe_db(operation="delete", table="iam_groups", method="delete_group_db") as obs:
        try:
            async with use_session(session) as s:
                result = await s.execute(delete(IamGroup).where(IamGroup.id == group_id))
            obs.success = result.rowcount > 0
            return obs.success
        except Exception:
            get_logger().warning("db_error", method="delete_group_db", exc_info=True)
            obs.success = False
            return False
