import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import SiteConfig
from nawa_api.utils.logger import get_logger


async def upsert_site_config_db(
    *,
    key: str,
    value: dict | list | bool | int | float | str,
    updated_by: uuid.UUID | None = None,
    session: AsyncSession | None = None,
) -> bool:
    with observe_db(operation="write", table="site_config", method="upsert_site_config_db") as obs:
        try:
            stmt = insert(SiteConfig).values(key=key, value=value, updated_by=updated_by)
            stmt = stmt.on_conflict_do_update(
                index_elements=[SiteConfig.key],
                set_={"value": value, "updated_by": updated_by},
            )
            async with use_session(session) as s:
                await s.execute(stmt)
            obs.success = True
            return True
        except Exception:
            get_logger().warning("db_error", method="upsert_site_config_db", exc_info=True)
            obs.success = False
            return False
