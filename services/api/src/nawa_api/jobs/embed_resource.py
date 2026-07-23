"""Embed a resource's corpus into resource_chunks (05-ai-infrastructure.md §9.2).

Deterministic chunking + a source_hash+model fingerprint make this idempotent:
re-running for an unchanged resource is a no-op, and seed pseudo-vectors
(embedding_model='seed') never match a real model, so the first live/mock pass
replaces them. Enqueued by the resource write services and by the seed script.
"""

from __future__ import annotations

import uuid
from hashlib import sha256

from nawa_api.ai.embeddings import embed, get_embeddings_provider
from nawa_api.ai.rag.chunking import chunk_resource
from nawa_api.db.resources.create_resource_chunk_db import create_resource_chunk_db
from nawa_api.db.resources.delete_resource_chunks_db import delete_resource_chunks_db
from nawa_api.db.resources.get_resource_db import get_resource_db
from nawa_api.db.resources.list_chunk_fingerprints_db import list_chunk_fingerprints_db
from nawa_api.db.utils import in_transaction
from nawa_api.utils.logger import get_logger


async def embed_resource(_ctx: dict | None = None, resource_id: str | uuid.UUID = "") -> int:
    rid = uuid.UUID(str(resource_id))
    resource = await get_resource_db(resource_id=rid)
    if resource is None or not resource.content:
        # Nothing to embed — clear any stale chunks and stop.
        await delete_resource_chunks_db(resource_id=rid)
        return 0

    drafts = chunk_resource(resource)
    model = get_embeddings_provider().name
    hashes = [sha256(d.content.encode("utf-8")).hexdigest() for d in drafts]
    desired = {d.chunk_index: (hashes[i], model) for i, d in enumerate(drafts)}

    if await list_chunk_fingerprints_db(resource_id=rid) == desired:
        return 0  # already up to date — idempotent no-op

    vectors = await embed([d.content for d in drafts], pii=False)  # institutional corpus

    async with in_transaction() as session:
        await delete_resource_chunks_db(resource_id=rid, session=session)
        for i, draft in enumerate(drafts):
            await create_resource_chunk_db(
                resource_id=rid,
                chunk_index=draft.chunk_index,
                content=draft.content,
                token_count=draft.token_count,
                source_hash=hashes[i],
                language=draft.language,
                heading_path=draft.heading_path,
                embedding=vectors[i],
                embedding_model=model,
                metadata=draft.metadata,
                session=session,
            )

    get_logger().info("embed_resource_complete", resource_id=str(rid), chunks=len(drafts))
    return len(drafts)
