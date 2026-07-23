import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import IamGroupMember
from nawa_api.utils.logger import get_logger


async def add_group_member_db(
    *, group_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession | None = None
) -> IamGroupMember | None:
    with observe_db(
        operation="write", table="iam_group_members", method="add_group_member_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = IamGroupMember(group_id=group_id, user_id=user_id)
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="add_group_member_db", exc_info=True)
            obs.success = False
            return None
