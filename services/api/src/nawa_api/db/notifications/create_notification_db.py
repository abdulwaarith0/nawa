import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.identity import Notification
from nawa_api.utils.logger import get_logger


async def create_notification_db(
    *,
    user_id: uuid.UUID,
    kind: str,
    title_ar: str | None = None,
    title_en: str | None = None,
    body_ar: str | None = None,
    body_en: str | None = None,
    payload: dict | None = None,
    session: AsyncSession | None = None,
) -> Notification | None:
    with observe_db(
        operation="write", table="notifications", method="create_notification_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = Notification(
                    user_id=user_id,
                    kind=kind,
                    title_ar=title_ar,
                    title_en=title_en,
                    body_ar=body_ar,
                    body_en=body_en,
                    payload=payload or {},
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_notification_db", exc_info=True)
            obs.success = False
            return None
