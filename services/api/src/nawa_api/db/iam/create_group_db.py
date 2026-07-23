import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import IamGroup
from nawa_api.utils.logger import get_logger


async def create_group_db(
    *,
    name: str,
    policy_ids: list[uuid.UUID] | None = None,
    description: str | None = None,
    managed: bool = False,
    session: AsyncSession | None = None,
) -> IamGroup | None:
    with observe_db(operation="write", table="iam_groups", method="create_group_db") as obs:
        try:
            async with use_session(session) as s:
                row = IamGroup(
                    name=name,
                    policy_ids=policy_ids or [],
                    description=description,
                    managed=managed,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_group_db", exc_info=True)
            obs.success = False
            return None
