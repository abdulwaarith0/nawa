import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import AssistantThread
from nawa_api.utils.logger import get_logger


async def create_assistant_thread_db(
    *,
    user_id: uuid.UUID,
    kind: str = "assistant",
    language: str = "ar",
    founder_profile_id: uuid.UUID | None = None,
    cohort_id: uuid.UUID | None = None,
    title: str | None = None,
    session: AsyncSession | None = None,
) -> AssistantThread | None:
    with observe_db(
        operation="write", table="assistant_threads", method="create_assistant_thread_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = AssistantThread(
                    user_id=user_id,
                    kind=kind,
                    language=language,
                    founder_profile_id=founder_profile_id,
                    cohort_id=cohort_id,
                    title=title,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_assistant_thread_db", exc_info=True)
            obs.success = False
            return None
