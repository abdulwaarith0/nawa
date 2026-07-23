import uuid

from sqlalchemy import delete

from nawa_api.db.utils import in_transaction
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import IamGroupMember
from nawa_api.utils.logger import get_logger


async def set_user_group_memberships_db(*, user_id: uuid.UUID, group_ids: list[uuid.UUID]) -> bool:
    """Replace a user's group memberships atomically (delete all, insert new)."""
    with observe_db(
        operation="write", table="iam_group_members", method="set_user_group_memberships_db"
    ) as obs:
        try:
            async with in_transaction() as s:
                await s.execute(delete(IamGroupMember).where(IamGroupMember.user_id == user_id))
                for group_id in group_ids:
                    s.add(IamGroupMember(user_id=user_id, group_id=group_id))
            obs.success = True
            return True
        except Exception:
            get_logger().warning("db_error", method="set_user_group_memberships_db", exc_info=True)
            obs.success = False
            return False
