import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import AssistantMessage
from nawa_api.utils.logger import get_logger


async def create_assistant_message_db(
    *,
    thread_id: uuid.UUID,
    role: str,
    content: str,
    language: str = "ar",
    citations: list | None = None,
    confidence: float | None = None,
    intent: str | None = None,
    session: AsyncSession | None = None,
) -> AssistantMessage | None:
    with observe_db(
        operation="write", table="assistant_messages", method="create_assistant_message_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = AssistantMessage(
                    thread_id=thread_id,
                    role=role,
                    content=content,
                    language=language,
                    citations=citations or [],
                    confidence=confidence,
                    intent=intent,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_assistant_message_db", exc_info=True)
            obs.success = False
            return None
