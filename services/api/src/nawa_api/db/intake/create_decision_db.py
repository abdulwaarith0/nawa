import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import Decision
from nawa_api.utils.logger import get_logger


async def create_decision_db(
    *,
    application_id: uuid.UUID,
    decided_by: uuid.UUID,
    decision: str,
    previous_value: dict | None = None,
    new_value: dict | None = None,
    reason: str | None = None,
    session: AsyncSession | None = None,
) -> Decision | None:
    with observe_db(operation="write", table="decisions", method="create_decision_db") as obs:
        try:
            async with use_session(session) as s:
                row = Decision(
                    application_id=application_id,
                    decided_by=decided_by,
                    decision=decision,
                    previous_value=previous_value or {},
                    new_value=new_value or {},
                    reason=reason,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_decision_db", exc_info=True)
            obs.success = False
            return None
