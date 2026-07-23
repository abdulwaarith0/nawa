import uuid
from types import SimpleNamespace

from nawa_api.ai.rag.chunking import (
    TARGET_TOKENS,
    ChunkDraft,
    _sentences,
    chunk_resource,
    estimate_tokens,
)


def _resource(content: str, language: str = "en"):
    return SimpleNamespace(id=uuid.uuid4(), content=content, language=language)


def test_estimate_tokens_heuristic():
    assert estimate_tokens("") == 1
    assert estimate_tokens("a" * 40) == 10


def test_empty_content_yields_no_chunks():
    assert chunk_resource(_resource("")) == []
    assert chunk_resource(_resource(None)) == []


def test_heading_path_is_preserved():
    content = "# Handbook\n## Round 2\nPrototyping happens here. Teams build fast."
    chunks = chunk_resource(_resource(content))
    assert len(chunks) == 1
    assert chunks[0].heading_path == ["Handbook", "Round 2"]


def test_chunk_index_increments_and_metadata_and_language_carried():
    content = "# A\none. two.\n# B\nthree. four."
    chunks = chunk_resource(_resource(content, language="ar"), metadata={"program_id": "sos"})
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(isinstance(c, ChunkDraft) for c in chunks)
    assert all(c.language == "ar" for c in chunks)
    assert all(c.metadata == {"program_id": "sos"} for c in chunks)


def _long_doc() -> str:
    sentences = [
        f"This is sentence number {i} describing robotics prototyping in the lab."
        for i in range(120)
    ]
    return "# Guide\n\n" + " ".join(sentences)


def test_large_segment_splits_with_overlap_and_bounded_size():
    chunks = chunk_resource(_resource(_long_doc()))
    assert len(chunks) >= 2
    # Packing bounds on the joined size, so no chunk exceeds the target.
    assert all(c.token_count <= TARGET_TOKENS for c in chunks)
    # Overlap: the last sentence of one chunk reappears in the next.
    tail = _sentences(chunks[0].content)[-1]
    assert tail in chunks[1].content


def test_never_splits_mid_sentence():
    content = _long_doc()
    chunks = chunk_resource(_resource(content))
    # Every source sentence appears whole inside some chunk.
    body = content.split("\n\n", 1)[1]
    for sentence in _sentences(body):
        assert any(sentence in c.content for c in chunks), sentence


def test_arabic_content_chunks_and_keeps_language():
    content = "# دليل\nالنموذج الأولي يُبنى هنا. الفرق تعمل بسرعة. المختبر متاح."
    chunks = chunk_resource(_resource(content, language="ar"))
    assert len(chunks) == 1
    assert chunks[0].language == "ar"
    assert chunks[0].heading_path == ["دليل"]
