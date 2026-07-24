import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import ApplicationDocument
from nawa_api.utils.logger import get_logger


async def list_application_documents_db(
    *, application_id: uuid.UUID, session: AsyncSession | None = None
) -> list[ApplicationDocument]:
    with observe_db(
        operation="read", table="application_documents", method="list_application_documents_db"
    ) as obs:
        try:
            stmt = select(ApplicationDocument).where(
                ApplicationDocument.application_id == application_id
            )
            async with use_session(session) as s:
                rows = (await s.execute(stmt)).scalars().all()
            obs.success = True
            return list(rows)
        except Exception:
            get_logger().warning(
                "db_error", method="list_application_documents_db", exc_info=True
            )
            obs.success = False
            return []
