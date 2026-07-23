from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import IamPolicy
from nawa_api.utils.logger import get_logger


async def upsert_policy_by_name_db(
    *,
    name: str,
    statements: list,
    managed: bool = True,
    session: AsyncSession | None = None,
) -> bool:
    """Idempotent upsert by unique name — pins managed rows back to the catalog
    even if they drifted in the DB (used by the boot seeder)."""
    with observe_db(
        operation="write", table="iam_policies", method="upsert_policy_by_name_db"
    ) as obs:
        try:
            stmt = insert(IamPolicy).values(name=name, statements=statements, managed=managed)
            stmt = stmt.on_conflict_do_update(
                index_elements=[IamPolicy.name],
                set_={"statements": statements, "managed": managed},
            )
            async with use_session(session) as s:
                await s.execute(stmt)
            obs.success = True
            return True
        except Exception:
            get_logger().warning("db_error", method="upsert_policy_by_name_db", exc_info=True)
            obs.success = False
            return False
