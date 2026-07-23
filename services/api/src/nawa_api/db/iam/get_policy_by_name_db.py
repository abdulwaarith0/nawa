from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import IamPolicy
from nawa_api.utils.logger import get_logger


async def get_policy_by_name_db(
    *, name: str, session: AsyncSession | None = None
) -> IamPolicy | None:
    with observe_db(operation="read", table="iam_policies", method="get_policy_by_name_db") as obs:
        try:
            async with use_session(session) as s:
                row = (
                    await s.execute(select(IamPolicy).where(IamPolicy.name == name))
                ).scalar_one_or_none()
            obs.success = row is not None
            return row
        except Exception:
            get_logger().warning("db_error", method="get_policy_by_name_db", exc_info=True)
            obs.success = False
            return None
