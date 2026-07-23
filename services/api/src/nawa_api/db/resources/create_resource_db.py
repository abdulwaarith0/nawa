import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.journey import Resource
from nawa_api.utils.logger import get_logger


async def create_resource_db(
    *,
    kind: str,
    title_ar: str | None = None,
    title_en: str | None = None,
    language: str = "ar",
    content: str | None = None,
    content_hash: str | None = None,
    tags: list[str] | None = None,
    status: str = "draft",
    steward_user_id: uuid.UUID | None = None,
    session: AsyncSession | None = None,
) -> Resource | None:
    with observe_db(operation="write", table="resources", method="create_resource_db") as obs:
        try:
            async with use_session(session) as s:
                row = Resource(
                    kind=kind,
                    title_ar=title_ar,
                    title_en=title_en,
                    language=language,
                    content=content,
                    content_hash=content_hash,
                    tags=tags or [],
                    status=status,
                    steward_user_id=steward_user_id,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_resource_db", exc_info=True)
            obs.success = False
            return None
