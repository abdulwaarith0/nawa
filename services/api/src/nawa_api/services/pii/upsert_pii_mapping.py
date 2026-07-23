import uuid

from nawa_api.ai.pii import PiiMapping
from nawa_api.db.pii.upsert_token_map_db import upsert_token_map_db


async def upsert_pii_mapping(
    *, subject_type: str, subject_id: uuid.UUID, mapping: PiiMapping
) -> PiiMapping:
    """Persist a subject's pseudonymizer mapping (extend-in-place semantics via
    the caller's `prior` mapping). UNCACHED — Postgres is the only home for PII
    (05-ai-infrastructure.md §5.2)."""
    row = await upsert_token_map_db(
        subject_type=subject_type, subject_id=subject_id, tokens=mapping.tokens
    )
    return PiiMapping(tokens=row.tokens if row else mapping.tokens)
