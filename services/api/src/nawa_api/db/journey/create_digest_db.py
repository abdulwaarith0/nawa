import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import Digest
from nawa_api.utils.logger import get_logger


async def create_digest_db(
    *,
    kind: str,
    scope_type: str,
    scope_id: uuid.UUID,
    period_start: date,
    period_end: date,
    stats: dict | None = None,
    at_risk: list | None = None,
    upcoming: list | None = None,
    content_ar: str | None = None,
    content_en: str | None = None,
    generated_by: str = "cron",
    status: str = "draft",
    session: AsyncSession | None = None,
) -> Digest | None:
    with observe_db(operation="write", table="digests", method="create_digest_db") as obs:
        try:
            async with use_session(session) as s:
                row = Digest(
                    kind=kind,
                    scope_type=scope_type,
                    scope_id=scope_id,
                    period_start=period_start,
                    period_end=period_end,
                    stats=stats or {},
                    at_risk=at_risk or [],
                    upcoming=upcoming or [],
                    content_ar=content_ar,
                    content_en=content_en,
                    generated_by=generated_by,
                    status=status,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_digest_db", exc_info=True)
            obs.success = False
            return None
