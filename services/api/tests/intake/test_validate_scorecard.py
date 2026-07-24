import uuid

import pytest

from nawa_api.ai.prompts.score_application import Citation, CriterionScore, ScorecardDraft
from nawa_api.contracts.errors import ApiError
from nawa_api.services.intake.validate_scorecard import validate_scorecard


def _draft(**criteria_kwargs) -> ScorecardDraft:
    defaults = dict(
        criterion_key="novelty",
        score=8,
        rationale_ar="ملاحظة",
        rationale_en="Note",
        citations=[Citation(source="answer:q1", quote="great idea")],
    )
    defaults.update(criteria_kwargs)
    return ScorecardDraft(
        criteria=[CriterionScore(**defaults)],
        rationale_ar="عام",
        rationale_en="Overall",
        confidence=0.8,
    )


def test_valid_draft_passes():
    draft = _draft()
    validate_scorecard(
        draft, criterion_keys={"novelty"}, original_answers={"q1": "This is a great idea."}
    )  # must not raise


def test_missing_criterion_key_rejected():
    draft = _draft()
    with pytest.raises(ApiError):
        validate_scorecard(
            draft,
            criterion_keys={"novelty", "feasibility"},  # draft only scores "novelty"
            original_answers={"q1": "This is a great idea."},
        )


def test_extra_criterion_key_rejected():
    draft = _draft()
    with pytest.raises(ApiError):
        validate_scorecard(
            draft,
            criterion_keys=set(),  # draft scores "novelty", rubric has no such key
            original_answers={"q1": "This is a great idea."},
        )


def test_citation_source_not_in_original_answers_rejected():
    draft = _draft(citations=[Citation(source="answer:q99", quote="anything")])
    with pytest.raises(ApiError):
        validate_scorecard(
            draft, criterion_keys={"novelty"}, original_answers={"q1": "This is a great idea."}
        )


def test_hallucinated_quote_rejected():
    # "q1" is real, but the quote never appears in it — a hallucination.
    draft = _draft(citations=[Citation(source="answer:q1", quote="something never said")])
    with pytest.raises(ApiError):
        validate_scorecard(
            draft, criterion_keys={"novelty"}, original_answers={"q1": "This is a great idea."}
        )


def test_quote_verbatim_check_is_whitespace_tolerant():
    draft = _draft(citations=[Citation(source="answer:q1", quote="great   idea")])
    validate_scorecard(
        draft, criterion_keys={"novelty"}, original_answers={"q1": "a great\nidea for sure"}
    )  # must not raise


def test_document_citation_resolves_against_document_texts():
    doc_id = uuid.uuid4()
    draft = _draft(citations=[Citation(source=f"document:{doc_id}", quote="extracted text")])
    validate_scorecard(
        draft,
        criterion_keys={"novelty"},
        original_answers={},
        document_texts={doc_id: "some extracted text here"},
    )  # must not raise


def test_document_citation_unknown_id_rejected():
    draft = _draft(citations=[Citation(source=f"document:{uuid.uuid4()}", quote="x")])
    with pytest.raises(ApiError):
        validate_scorecard(
            draft, criterion_keys={"novelty"}, original_answers={}, document_texts={}
        )


def test_malformed_document_source_rejected():
    draft = _draft(citations=[Citation(source="document:not-a-uuid", quote="x")])
    with pytest.raises(ApiError):
        validate_scorecard(draft, criterion_keys={"novelty"}, original_answers={})


def test_unknown_source_scheme_rejected():
    draft = _draft(citations=[Citation(source="carrier-pigeon:q1", quote="x")])
    with pytest.raises(ApiError):
        validate_scorecard(
            draft, criterion_keys={"novelty"}, original_answers={"q1": "x present here"}
        )
