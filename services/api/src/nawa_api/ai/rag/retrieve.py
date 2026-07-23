"""Citation-ready retrieval (05-ai-infrastructure.md §9.3).

Embeds the query, runs the filtered pgvector search, drops anything below
RAG_MIN_SCORE. If nothing survives, the answer path says "no supporting source
found" rather than free-associating.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from nawa_api.ai.embeddings import embed
from nawa_api.db.rag.search_chunks_db import search_chunks_db

RAG_MIN_SCORE = 0.25


class RetrievalFilters(BaseModel):
    program_id: str | None = None
    language: str | None = None
    resource_type: str | None = None
    audience: str | None = None


class RetrievedChunk(BaseModel):
    chunk_id: uuid.UUID
    resource_id: uuid.UUID
    heading_path: list[str] = Field(default_factory=list)
    content: str
    score: float


async def retrieve(
    query: str, *, k: int = 8, filters: RetrievalFilters | None = None
) -> list[RetrievedChunk]:
    filters = filters or RetrievalFilters()
    vectors = await embed([query], pii=False)  # searching institutional corpus
    rows = await search_chunks_db(
        query_embedding=vectors[0],
        k=k,
        program_id=filters.program_id,
        language=filters.language,
        resource_type=filters.resource_type,
        audience=filters.audience,
    )
    return [
        RetrievedChunk(
            chunk_id=chunk.id,
            resource_id=chunk.resource_id,
            heading_path=chunk.heading_path,
            content=chunk.content,
            score=score,
        )
        for chunk, score in rows
        if score >= RAG_MIN_SCORE
    ]
