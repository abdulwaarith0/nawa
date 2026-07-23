import uuid

from nawa_api.ai.prompts.rag_answer import Citation, RagAnswer
from nawa_api.ai.rag import answer as answer_mod
from nawa_api.ai.rag.answer import answer_question
from nawa_api.ai.rag.retrieve import RetrievedChunk


def _chunk(content: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(), resource_id=uuid.uuid4(), content=content, score=0.9
    )


async def test_no_chunks_returns_unsupported(monkeypatch):
    async def fake_retrieve(question, *, k=8, filters=None):
        return []

    monkeypatch.setattr(answer_mod, "retrieve", fake_retrieve)
    result = await answer_question("what is round 2?")
    assert result.confidence == "unsupported"
    assert result.citations == []
    assert "No supporting source" in result.answer


async def test_valid_citations_resolve_to_real_chunk_ids(monkeypatch):
    c1, c2 = _chunk("alpha"), _chunk("beta")

    async def fake_retrieve(question, *, k=8, filters=None):
        return [c1, c2]

    async def fake_structured(request, schema, **kwargs):
        obj = RagAnswer(
            answer="Because of the handbook.",
            citations=[Citation(chunk_id=1, quote="alpha"), Citation(chunk_id=2, quote="beta")],
            confidence="supported",
        )
        return obj, None

    monkeypatch.setattr(answer_mod, "retrieve", fake_retrieve)
    monkeypatch.setattr("nawa_api.ai.gateway.complete_structured", fake_structured)

    result = await answer_question("why?")
    assert result.confidence == "supported"
    assert {c.chunk_id for c in result.citations} == {c1.chunk_id, c2.chunk_id}


async def test_hallucinated_citation_ids_are_dropped(monkeypatch):
    c1 = _chunk("only")

    async def fake_retrieve(question, *, k=8, filters=None):
        return [c1]

    async def fake_structured(request, schema, **kwargs):
        # [99] was never retrieved — a hallucinated id.
        obj = RagAnswer(
            answer="Made up.",
            citations=[Citation(chunk_id=99, quote="nope")],
            confidence="supported",
        )
        return obj, None

    monkeypatch.setattr(answer_mod, "retrieve", fake_retrieve)
    monkeypatch.setattr("nawa_api.ai.gateway.complete_structured", fake_structured)

    result = await answer_question("why?")
    assert result.citations == []
    assert result.confidence == "unsupported"
