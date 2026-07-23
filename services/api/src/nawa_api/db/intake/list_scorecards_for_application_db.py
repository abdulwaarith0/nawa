import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Scorecard
from nawa_api.utils.logger import get_logger


async def list_scorecards_for_application_db(
    *, application_id: uuid.UUID, session: AsyncSession | None = None
) -> list[Scorecard]:
    with observe_db(
        operation="read", table="scorecards", method="list_scorecards_for_application_db"
    ) as obs:
        try:
            stmt = (
                select(Scorecard)
                .where(Scorecard.application_id == application_id)
                .order_by(Scorecard.created_at.desc())
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning(
                "db_error", method="list_scorecards_for_application_db", exc_info=True
            )
            obs.success = False
            return []
