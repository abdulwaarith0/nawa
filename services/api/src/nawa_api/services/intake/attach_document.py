"""Document attachment (06-intake-copilot.md §2.1). Streams a file through
the standard object-storage pipeline (private bucket, presigned GETs,
content-addressed keys) and records it in `application_documents`.
"""

from __future__ import annotations

import uuid
from hashlib import sha256

from nawa_api.contracts.errors import ERR_NOT_FOUND
from nawa_api.db.intake.create_application_document_db import create_application_document_db
from nawa_api.db.intake.get_application_db import get_application_db
from nawa_api.runtime.storage import get_storage_provider
from nawa_api.utils.invalidate_cache_keys import invalidate_cache_keys

_VALID_KINDS = frozenset({"attachment", "cv", "deck", "extracted_text"})


async def attach_document(
    *,
    application_id: uuid.UUID,
    filename: str,
    content: bytes,
    mime_type: str,
    kind: str = "attachment",
) -> dict:
    if kind not in _VALID_KINDS:
        kind = "attachment"

    application = await get_application_db(application_id=application_id)
    if application is None:
        raise ERR_NOT_FOUND

    digest = sha256(content).hexdigest()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    storage_key = f"intake/documents/{application_id}/{digest}.{ext}"
    await get_storage_provider().put_object(storage_key, content, content_type=mime_type)

    doc = await create_application_document_db(
        application_id=application_id,
        storage_key=storage_key,
        file_name=filename,
        mime_type=mime_type,
        size_bytes=len(content),
        kind=kind,
    )
    if doc is None:
        raise ERR_NOT_FOUND

    # get_scorecard's cached `documents` list embeds a presigned URL per
    # document, so a new attachment must invalidate it the same way scoring/
    # hidden-gem/dedup/decision writes already do.
    await invalidate_cache_keys(f"services:intake:get_scorecard:{application_id}")

    return {
        "id": str(doc.id),
        "file_name": doc.file_name,
        "mime_type": doc.mime_type,
        "kind": doc.kind,
        "size_bytes": doc.size_bytes,
        "created_at": doc.created_at.isoformat(),
    }
