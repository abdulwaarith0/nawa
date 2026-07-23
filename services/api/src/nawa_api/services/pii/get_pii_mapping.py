import uuid

from nawa_api.ai.pii import PiiMapping
from nawa_api.db.pii.get_token_map_db import get_token_map_db


async def get_pii_mapping(*, subject_type: str, subject_id: uuid.UUID) -> PiiMapping:
    """Load a subject's persisted pseudonymizer mapping (empty if none).

    DELIBERATELY UNCACHED (05-ai-infrastructure.md §5.2 / §11): PII mappings go
    straight to Postgres and are never mirrored to Redis — a cached copy of PII
    multiplies the attack surface.
    """
    row = await get_token_map_db(subject_type=subject_type, subject_id=subject_id)
    return PiiMapping(tokens=row.tokens if row else {})
