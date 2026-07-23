from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from nawa_api.ai.prompts import PROMPT_REGISTRY, TEMPLATE_FILES, get_template
from nawa_api.ai.prompts.base import PromptTemplate
from nawa_api.ai.prompts.detect_language import DetectLanguageInput
from nawa_api.ai.prompts.score_application import ScoreApplicationInput
from nawa_api.ai.types import Tier


def test_registry_has_the_slice_five_templates():
    assert set(PROMPT_REGISTRY) == {
        "intake.detect_language",
        "intake.normalize",
        "intake.score",
        "intake.hidden_gem",
        "assistant.answer",
    }


def test_render_stamps_task_and_version_and_tier():
    tmpl = get_template("intake.score")
    req = tmpl.render(
        ScoreApplicationInput(rubric="R", criteria=["novelty"], application_text="A")
    )
    assert req.task == "intake.score"
    assert req.prompt_version == "v1"
    assert req.tier is Tier.LARGE
    assert "R" in req.messages[0]["content"]
    assert "novelty" in req.messages[0]["content"]


def test_render_is_deterministic():
    tmpl = get_template("intake.detect_language")
    a = tmpl.render({"text": "مرحبا"})
    b = tmpl.render({"text": "مرحبا"})
    assert a.model_dump() == b.model_dump()


def test_render_missing_field_raises():
    with pytest.raises(ValidationError):
        get_template("intake.detect_language").render({})


def test_render_extra_field_raises():
    with pytest.raises(ValidationError):
        get_template("intake.detect_language").render({"text": "x", "sneaky": 1})


def test_render_wrong_model_type_raises():
    # A detect-language template can't render a score input.
    with pytest.raises(TypeError):
        get_template("intake.detect_language").render(
            ScoreApplicationInput(rubric="r", criteria=[], application_text="a")
        )


def test_render_accepts_a_matching_model_instance():
    req = get_template("intake.detect_language").render(DetectLanguageInput(text="hello"))
    assert "hello" in req.messages[0]["content"]


def test_fingerprint_changes_when_system_text_changes():
    class In(BaseModel):
        x: str

    class Out(BaseModel):
        y: str

    base_kwargs = dict(
        task="t",
        version="v1",
        tier=Tier.SMALL,
        input_schema=In,
        output_schema=Out,
        languages=("en",),
        user_template="{x}",
    )
    a = PromptTemplate(system="alpha", **base_kwargs)
    a_again = PromptTemplate(system="alpha", **base_kwargs)
    b = PromptTemplate(system="beta", **base_kwargs)
    assert a.fingerprint() == a_again.fingerprint()
    assert a.fingerprint() != b.fingerprint()


def test_every_template_file_has_a_changelog_mentioning_its_version():
    for task, template in PROMPT_REGISTRY.items():
        text = Path(TEMPLATE_FILES[task]).read_text(encoding="utf-8")
        assert "# CHANGELOG:" in text, f"{task} file missing a CHANGELOG block"
        assert template.version in text, f"{task} CHANGELOG does not mention {template.version}"
