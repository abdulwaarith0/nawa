import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import ApplicationUpload
from nawa_api.utils.logger import get_logger


async def create_application_upload_db(
    *,
    cycle_id: uuid.UUID,
    storage_key: str,
    file_name: str,
    mime_type: str,
    size_bytes: int,
    uploaded_by_user_id: uuid.UUID,
    row_count: int | None = None,
    session: AsyncSession | None = None,
) -> ApplicationUpload | None:
    with observe_db(
        operation="write", table="application_uploads", method="create_application_upload_db"
    ) as obs:
        try:
            async with use_session(session) as s:
                row = ApplicationUpload(
                    cycle_id=cycle_id,
                    storage_key=storage_key,
                    file_name=file_name,
                    mime_type=mime_type,
                    size_bytes=size_bytes,
                    row_count=row_count,
                    uploaded_by_user_id=uploaded_by_user_id,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_application_upload_db", exc_info=True)
            obs.success = False
            return None
