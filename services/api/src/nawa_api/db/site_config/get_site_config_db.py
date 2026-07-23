from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import SiteConfig
from nawa_api.utils.logger import get_logger


async def get_site_config_db(*, key: str, session: AsyncSession | None = None):
    with observe_db(operation="read", table="site_config", method="get_site_config_db") as obs:
        try:
            async with use_session(session) as s:
                row = (
                    await s.execute(select(SiteConfig).where(SiteConfig.key == key))
                ).scalar_one_or_none()
            obs.success = row is not None
            return row.value if row is not None else None
        except Exception:
            get_logger().warning("db_error", method="get_site_config_db", exc_info=True)
            obs.success = False
            return None
