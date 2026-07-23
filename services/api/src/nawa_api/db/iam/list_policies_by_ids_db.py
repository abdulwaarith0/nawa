import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import IamPolicy
from nawa_api.utils.logger import get_logger


async def list_policies_by_ids_db(
    *, policy_ids: list[uuid.UUID], session: AsyncSession | None = None
) -> list[IamPolicy]:
    if not policy_ids:
        return []
    with observe_db(
        operation="read", table="iam_policies", method="list_policies_by_ids_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                rows = (
                    (await s.execute(select(IamPolicy).where(IamPolicy.id.in_(policy_ids))))
                    .scalars()
                    .all()
                )
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_policies_by_ids_db", exc_info=True)
            obs.success = False
            return []
