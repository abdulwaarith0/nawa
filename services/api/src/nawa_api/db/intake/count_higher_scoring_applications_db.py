import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Application
from nawa_api.utils.logger import get_logger


async def count_higher_scoring_applications_db(
    *, cycle_id: uuid.UUID, total_score: float, session: AsyncSession | None = None
) -> int:
    """Competition-style rank support: count of scored applications in the
    cycle with a STRICTLY higher total_score. `rank = count + 1` — ties share
    a rank, so this degrades safely without needing a window function."""
    with observe_db(
        operation="read",
        table="applications",
        method="count_higher_scoring_applications_db",
    ) as obs:
        try:
            stmt = select(func.count()).select_from(Application).where(
                Application.cycle_id == cycle_id,
                Application.ai_total_score.isnot(None),
                Application.ai_total_score > total_score,
            )
            async with use_session(session) as s:
                count = (await s.execute(stmt)).scalar_one()
            obs.success = True
            return int(count)
        except Exception:
            get_logger().warning(
                "db_error", method="count_higher_scoring_applications_db", exc_info=True
            )
            obs.success = False
            return 0
