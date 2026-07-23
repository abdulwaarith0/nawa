import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import clamp_pagination, use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.ai import AiCall
from nawa_api.utils.logger import get_logger


async def list_ai_calls_db(
    *,
    task: str | None = None,
    provider: str | None = None,
    status: str | None = None,
    cycle_id: uuid.UUID | None = None,
    limit: int | None = None,
    offset: int | None = None,
    session: AsyncSession | None = None,
) -> list[AiCall]:
    clamped_limit, clamped_offset = clamp_pagination(limit=limit, offset=offset)
    with observe_db(operation="read", table="ai_calls", method="list_ai_calls_db") as obs:
        try:
            stmt = select(AiCall)
            if task is not None:
                stmt = stmt.where(AiCall.task == task)
            if provider is not None:
                stmt = stmt.where(AiCall.provider == provider)
            if status is not None:
                stmt = stmt.where(AiCall.status == status)
            if cycle_id is not None:
                stmt = stmt.where(AiCall.cycle_id == cycle_id)
            stmt = (
                stmt.order_by(AiCall.created_at.desc())
                .limit(clamped_limit)
                .offset(clamped_offset)
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning("db_error", method="list_ai_calls_db", exc_info=True)
            obs.success = False
            return []
