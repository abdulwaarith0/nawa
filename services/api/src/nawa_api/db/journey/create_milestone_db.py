import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import Milestone
from nawa_api.utils.logger import get_logger


async def create_milestone_db(
    *,
    program_id: uuid.UUID,
    sequence: int,
    scope: str = "template",
    program_cycle_id: uuid.UUID | None = None,
    cohort_id: uuid.UUID | None = None,
    template_id: uuid.UUID | None = None,
    title_ar: str | None = None,
    title_en: str | None = None,
    description_ar: str | None = None,
    description_en: str | None = None,
    due_offset_days: int | None = None,
    due_date: date | None = None,
    evidence_required: bool = False,
    config: dict | None = None,
    session: AsyncSession | None = None,
) -> Milestone | None:
    with observe_db(operation="write", table="milestones", method="create_milestone_db") as obs:
        try:
            async with use_session(session) as s:
                row = Milestone(
                    program_id=program_id,
                    sequence=sequence,
                    scope=scope,
                    program_cycle_id=program_cycle_id,
                    cohort_id=cohort_id,
                    template_id=template_id,
                    title_ar=title_ar,
                    title_en=title_en,
                    description_ar=description_ar,
                    description_en=description_en,
                    due_offset_days=due_offset_days,
                    due_date=due_date,
                    evidence_required=evidence_required,
                    config=config or {},
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_milestone_db", exc_info=True)
            obs.success = False
            return None
