"""Heading-aware corpus chunking (05-ai-infrastructure.md §9.1).

Pure function: `chunk_resource(resource) -> list[ChunkDraft]`. Target ~800 tokens
per chunk with ~120-token overlap, measured with a cheap len//4 heuristic (exact
tokenization isn't worth a network call here). Splits on Markdown headings
first, then sentences — never mid-sentence — and preserves the heading path into
each chunk so citations render with context.
"""

from __future__ import annotations

import re
import uuid
from typing import Protocol

from pydantic import BaseModel

TARGET_TOKENS = 800
OVERLAP_TOKENS = 120

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
# Split after sentence enders (Latin + Arabic ؟ ، ) or on blank lines.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?؟])\s+|\n\s*\n")


class ChunkableResource(Protocol):
    id: uuid.UUID
    content: str | None
    language: str


class ChunkDraft(BaseModel):
    resource_id: uuid.UUID
    chunk_index: int
    content: str
    heading_path: list[str]
    language: str
    token_count: int
    metadata: dict


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def _pack(text: str) -> list[str]:
    """Greedily pack whole sentences to ~TARGET_TOKENS, carrying ~OVERLAP_TOKENS
    of trailing sentences into the next chunk. Bounds on the joined size so a
    chunk's stored token_count never exceeds the target (barring a single
    sentence that is itself over-length)."""
    sentences = _sentences(text)
    if not sentences:
        return []
    chunks: list[str] = []
    current: list[str] = []
    for sentence in sentences:
        if current and estimate_tokens(" ".join([*current, sentence])) > TARGET_TOKENS:
            chunks.append(" ".join(current))
            overlap: list[str] = []
            overlap_tokens = 0
            for prev in reversed(current):
                pt = estimate_tokens(prev)
                if overlap_tokens + pt > OVERLAP_TOKENS:
                    break
                overlap.insert(0, prev)
                overlap_tokens += pt
            current = overlap
        current.append(sentence)
    if current:
        chunks.append(" ".join(current))
    return chunks


def _segments(content: str) -> list[tuple[list[str], str]]:
    """Split content into (heading_path, text) segments on Markdown headings."""
    heading_stack: list[tuple[int, str]] = []
    buffer: list[str] = []
    segments: list[tuple[list[str], str]] = []

    def flush() -> None:
        text = "\n".join(buffer).strip()
        if text:
            segments.append(([title for _, title in heading_stack], text))
        buffer.clear()

    for line in content.splitlines():
        heading = _HEADING_RE.match(line.strip())
        if heading:
            flush()
            level = len(heading.group(1))
            heading_stack[:] = [h for h in heading_stack if h[0] < level]
            heading_stack.append((level, heading.group(2).strip()))
        else:
            buffer.append(line)
    flush()
    return segments


def chunk_resource(
    resource: ChunkableResource, *, metadata: dict | None = None
) -> list[ChunkDraft]:
    content = resource.content or ""
    drafts: list[ChunkDraft] = []
    index = 0
    for heading_path, text in _segments(content):
        for chunk_text in _pack(text):
            drafts.append(
                ChunkDraft(
                    resource_id=resource.id,
                    chunk_index=index,
                    content=chunk_text,
                    heading_path=heading_path,
                    language=resource.language,
                    token_count=estimate_tokens(chunk_text),
                    metadata=metadata or {},
                )
            )
            index += 1
    return drafts
