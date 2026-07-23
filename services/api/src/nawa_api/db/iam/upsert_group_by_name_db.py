import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import IamGroup
from nawa_api.utils.logger import get_logger


async def upsert_group_by_name_db(
    *,
    name: str,
    policy_ids: list[uuid.UUID],
    managed: bool = True,
    session: AsyncSession | None = None,
) -> bool:
    with observe_db(operation="write", table="iam_groups", method="upsert_group_by_name_db") as obs:
        try:
            stmt = insert(IamGroup).values(name=name, policy_ids=policy_ids, managed=managed)
            stmt = stmt.on_conflict_do_update(
                index_elements=[IamGroup.name],
                set_={"policy_ids": policy_ids, "managed": managed},
            )
            async with use_session(session) as s:
                await s.execute(stmt)
            obs.success = True
            return True
        except Exception:
            get_logger().warning("db_error", method="upsert_group_by_name_db", exc_info=True)
            obs.success = False
            return False
