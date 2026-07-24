import uuid

import pytest

from nawa_api.ai.prompts.hidden_gem_review import HiddenGemReview
from nawa_api.ai.prompts.score_application import Citation
from nawa_api.contracts.errors import ApiError
from nawa_api.services.intake.validate_hidden_gem_review import validate_hidden_gem_review


def _review(**kwargs) -> HiddenGemReview:
    defaults = dict(
        is_hidden_gem=True,
        reason_ar="فكرة قوية بلغة ضعيفة",
        reason_en="A strong idea in weak prose",
        citations=[Citation(source="answer:idea", quote="low-cost water sensors")],
    )
    defaults.update(kwargs)
    return HiddenGemReview(**defaults)


def test_valid_review_passes():
    validate_hidden_gem_review(
        _review(), original_answers={"idea": "we build low-cost water sensors"}
    )  # must not raise


def test_citation_source_not_in_original_answers_rejected():
    review = _review(citations=[Citation(source="answer:missing", quote="x")])
    with pytest.raises(ApiError):
        validate_hidden_gem_review(review, original_answers={"idea": "water sensors"})


def test_hallucinated_quote_rejected():
    review = _review(citations=[Citation(source="answer:idea", quote="never said this")])
    with pytest.raises(ApiError):
        validate_hidden_gem_review(review, original_answers={"idea": "water sensors"})


def test_document_citation_resolves_against_document_texts():
    doc_id = uuid.uuid4()
    review = _review(citations=[Citation(source=f"document:{doc_id}", quote="extracted text")])
    validate_hidden_gem_review(
        review, original_answers={}, document_texts={doc_id: "some extracted text here"}
    )  # must not raise


def test_is_hidden_gem_false_still_validates_citations():
    review = _review(is_hidden_gem=False, citations=[Citation(source="answer:idea", quote="x")])
    with pytest.raises(ApiError):
        validate_hidden_gem_review(review, original_answers={"idea": "water sensors"})
