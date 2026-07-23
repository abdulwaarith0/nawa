from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import IamPolicy
from nawa_api.utils.logger import get_logger


async def create_policy_db(
    *,
    name: str,
    statements: list,
    description: str | None = None,
    managed: bool = False,
    session: AsyncSession | None = None,
) -> IamPolicy | None:
    with observe_db(operation="write", table="iam_policies", method="create_policy_db") as obs:
        try:
            async with use_session(session) as s:
                row = IamPolicy(
                    name=name, statements=statements, description=description, managed=managed
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_policy_db", exc_info=True)
            obs.success = False
            return None
