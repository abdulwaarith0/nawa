import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import IamGroupMember
from nawa_api.utils.logger import get_logger


async def list_user_group_ids_db(
    *, user_id: uuid.UUID, session: AsyncSession | None = None
) -> list[uuid.UUID]:
    with observe_db(
        operation="read", table="iam_group_members", method="list_user_group_ids_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                rows = (
                    (
                        await s.execute(
                            select(IamGroupMember.group_id).where(IamGroupMember.user_id == user_id)
                        )
                    )
                    .scalars()
                    .all()
                )
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_user_group_ids_db", exc_info=True)
            obs.success = False
            return []
