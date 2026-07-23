import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from nawa_api.db.utils import use_session
from nawa_api.metrics.db import observe_db
from nawa_api.models.intake import ApplicationDocument
from nawa_api.utils.logger import get_logger


async def create_application_document_db(
    *,
    application_id: uuid.UUID,
    storage_key: str,
    file_name: str,
    mime_type: str,
    size_bytes: int,
    kind: str = "attachment",
    extracted_text: str | None = None,
    session: AsyncSession | None = None,
) -> ApplicationDocument | None:
    with observe_db(
        operation="write",
        table="application_documents",
        method="create_application_document_db",
    ) as obs:
        try:
            async with use_session(session) as s:
                row = ApplicationDocument(
                    application_id=application_id,
                    storage_key=storage_key,
                    file_name=file_name,
                    mime_type=mime_type,
                    size_bytes=size_bytes,
                    kind=kind,
                    extracted_text=extracted_text,
                )
                s.add(row)
                await s.flush()
                await s.refresh(row)
            obs.success = True
            return row
        except Exception:
            get_logger().warning("db_error", method="create_application_document_db", exc_info=True)
            obs.success = False
            return None
