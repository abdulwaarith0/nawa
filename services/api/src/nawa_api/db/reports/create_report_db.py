import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.reports import Report
from nawa_api.utils.logger import get_logger


async def create_report_db(
    *,
    kind: str,
    subject_type: str,
    period_start: date,
    period_end: date,
    subject_id: uuid.UUID | None = None,
    template_key: str | None = None,
    content: dict | None = None,
    rendered_ar: str | None = None,
    rendered_en: str | None = None,
    status: str = "draft",
    generated_by: str = "ai",
    session: AsyncSession | None = None,
) -> Report | None:
    with observe_db(operation="write", table="reports", method="create_report_db") as obs:
        try:
            async with use_session(session) as s:
                row = Report(
                    kind=kind,
                    subject_type=subject_type,
                    subject_id=subject_id,
                    period_start=period_start,
                    period_end=period_end,
                    template_key=template_key,
                    content=content or {},
                    rendered_ar=rendered_ar,
                    rendered_en=rendered_en,
                    status=status,
                    generated_by=generated_by,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_report_db", exc_info=True)
            obs.success = False
            return None
