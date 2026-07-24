"""Semantic-dedup embedding (06-intake-copilot.md §4, 03-data-spine.md §6).

Embeds the normalized-EN `title + summary` — 03's designated embedding input
— pseudonymized (`pii=True`: unlike the institutional resource corpus, this
is applicant text) into the `application_embeddings` side-table. Idempotent
via the same source_hash+model fingerprint pattern as `embed_resource.py`:
unchanged text + model is a no-op, and the seed's deterministic pseudo-vectors
(`embedding_model='seed-deterministic-v1'`) never match a real provider's
name, so the first real run always replaces them.
"""

from __future__ import annotations

import uuid
from hashlib import sha256

from nawa_api.ai.embeddings import embed, get_embeddings_provider
from nawa_api.db.intake.create_application_embedding_db import create_application_embedding_db
from nawa_api.db.intake.get_application_db import get_application_db
from nawa_api.db.intake.get_application_embedding_db import get_application_embedding_db


def _embedding_text(application) -> str:
    return f"{application.title or ''}\n{application.summary or ''}"


async def embed_application(
    _ctx: dict | None = None, application_id: str | uuid.UUID = ""
) -> str:
    aid = uuid.UUID(str(application_id))
    application = await get_application_db(application_id=aid)
    if application is None:
        return "missing"

    text = _embedding_text(application)
    desired_hash = sha256(text.encode("utf-8")).hexdigest()
    model = get_embeddings_provider().name

    existing = await get_application_embedding_db(application_id=aid)
    unchanged = (
        existing is not None
        and existing.source_hash == desired_hash
        and existing.embedding_model == model
    )
    if unchanged:
        return "unchanged"

    vector = (await embed([text], pii=True))[0]
    await create_application_embedding_db(
        application_id=aid, embedding=vector, embedding_model=model, source_hash=desired_hash
    )
    return "embedded"
