from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import SiteConfig
from nawa_api.utils.logger import get_logger


async def list_all_site_config_db(*, session: AsyncSession | None = None) -> dict:
    with observe_db(operation="read", table="site_config", method="list_all_site_config_db") as obs:
        try:
            async with use_session(session) as s:
                rows = (await s.execute(select(SiteConfig))).scalars().all()
            obs.success = True
            return {row.key: row.value for row in rows}
        except Exception:
            get_logger().warning("db_error", method="list_all_site_config_db", exc_info=True)
            obs.success = False
            return {}
