"""Offline literal-contract witnesses, not reconstructions of discarded prose."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from storyforge.config import AppSettings
from storyforge.development.v2 import load_profiles_v2
from storyforge.domain.story_v2 import EducationalTarget, StoryRequestV2, StoryV2
from storyforge.llm.fake import FakeProvider, FakeStep
from storyforge.llm.fixtures_v2 import fixture_steps_v2
from storyforge.orchestration.budget import BudgetLimits
from storyforge.orchestration.engine import StoryEngine
from storyforge.prompts.v2 import build_request_v2, WRITER_VERSION_V2
from storyforge.quality.gate import assess_story
from storyforge.quality.text import name_spans
from storyforge.validation.normalization_v2 import normalize_v2
from storyforge.validation.output_diagnostics import export_validation_diagnostics

EXAMPLES = Path(__file__).resolve().parents[1] / "docs/examples"
SETTINGS = AppSettings(planner_output_tokens=6144, writer_output_tokens=16384, max_input_tokens=32000)
LIMITS = BudgetLimits(max_total_tokens=140000)
FORMS = [(23, "ך", "כ", "מלך", "כף"), (24, "ם", "מ", "ים", "מם"),
         (25, "ן", "נ", "גן", "נון"), (26, "ף", "פ", "אף", "פא"), (27, "ץ", "צ", "עץ", "צדי")]


@pytest.fixture
def book():
    req = StoryRequestV2.model_validate_json((EXAMPLES / "roy-alphabet-request.v2.he.json").read_text(encoding="utf-8"))
    brief = normalize_v2(req, load_profiles_v2(), settings=SETTINGS)
    plan, story = fixture_steps_v2(brief)
    return req, brief, plan, json.loads(story.response_json)


def words(base, final, example):
    return [f"רועי גילה שבסוף מילה {base} נכתבת {final}, כמו במילה {example}.",
            "הוא פתח שער והחברים המשיכו יחד."]


@pytest.mark.parametrize("page,final,base,example,letter_name", FORMS)
@pytest.mark.parametrize("style", ["plain", "quoted", "hebrew_quoted"])
def test_all_five_final_form_pairs_and_examples_pass_unchanged_gate(book, page, final, base, example, letter_name, style):
    req, brief, _, raw = book
    target = req.structure.targets[page - 1]
    assert (target.label, target.base_form, target.example_word) == (final, base, example)
    symbol = {"plain": base, "quoted": f'"{base}"', "hebrew_quoted": f'״{base}״'}[style]
    raw["pages"][page - 1]["sentence_units"] = words(symbol, final, example)
    story = StoryV2.model_validate_json(json.dumps(raw)).validate_for(brief)
    assert assess_story(story, brief).passed
    assert len(story.pages) == 27
    assert tuple(p.target_id for p in story.pages) == tuple(t.target_id for t in req.structure.targets)


@pytest.mark.parametrize("page,final,base,example,letter_name", FORMS)
@pytest.mark.parametrize("style", ["omitted", "prefixed", "letter_name", "pointed"])
def test_base_form_must_be_exact_standalone_symbol(book, page, final, base, example, letter_name, style):
    _, brief, _, raw = book
    symbol = {"omitted": "האות", "prefixed": "מ" + base, "letter_name": letter_name, "pointed": base + "\u05b0"}[style]
    assert not name_spans(symbol, base)
    raw["pages"][page - 1]["sentence_units"] = words(symbol, final, example)
    report = assess_story(raw, brief)
    assert not report.passed
    assert [(i.code, i.page_number) for i in report.issues if i.severity != "advisory"] == [
        ("TARGET_BASE_FORM_MISSING", page)]


@pytest.mark.parametrize("page,final,base,example,letter_name", FORMS)
def test_example_must_be_exact_word_not_only_prefixed_word(book, page, final, base, example, letter_name):
    _, brief, _, raw = book
    raw["pages"][page - 1]["sentence_units"] = words(base, final, "ב" + example)
    report = assess_story(raw, brief)
    assert any(i.code == "TARGET_EXAMPLE_MISSING" and i.page_number == page for i in report.issues)
    assert not report.passed


@pytest.mark.parametrize("page,final,base,example,letter_name", FORMS)
def test_supplied_example_must_end_in_requested_final_form(page, final, base, example, letter_name):
    EducationalTarget(target_id="final", label=final, kind="letter", base_form=base, example_word=example)
    with pytest.raises(ValidationError):
        EducationalTarget(target_id="final", label=final, kind="letter", base_form=base, example_word=example + "א")
    with pytest.raises(ValidationError):
        EducationalTarget(target_id="final", label=final, kind="letter", base_form=base, example_word=example[:-1] + base)


@pytest.mark.parametrize("page,final,base,example,letter_name", FORMS)
def test_ending_example_does_not_replace_separate_final_symbol(book, page, final, base, example, letter_name):
    _, brief, _, raw = book
    raw["pages"][page - 1]["sentence_units"] = words(base, "האות", example)
    report = assess_story(raw, brief)
    assert any(i.code == "TARGET_LABEL_MISSING" and i.page_number == page for i in report.issues)


def test_same_sentence_is_writer_guidance_not_a_new_gate_rule(book):
    _, brief, _, raw = book
    raw["pages"][22]["sentence_units"] = ["רועי פגש את כ בדרך לשער הקסום.",
        "בסוף מילה האות נכתבת ך, כמו במילה מלך."]
    assert assess_story(raw, brief).passed


def test_writer_instructions_match_literal_gate_without_new_calls(book):
    _, brief, plan, _ = book
    from storyforge.domain.story_v2 import StoryPlanV2
    request = build_request_v2("writer", brief, "scripted-v1", brief.execution.writer_output_tokens, 45.0,
                               plan=StoryPlanV2.model_validate_json(plan.response_json))
    assert request.prompt_version == WRITER_VERSION_V2 == "writer-v2-3"
    for phrase in ("standalone written symbols", "same short, natural explanatory sentence",
                   "attached prefix", "END of a word", "child's action", "sentence-unit limits"):
        assert phrase in request.instructions
    assert request.max_output_tokens == brief.execution.writer_output_tokens
    planner = build_request_v2("planner", brief, "scripted-v1", brief.execution.planner_output_tokens, 45.0)
    assert planner.prompt_version == "planner-v2-1"


def test_context_failure_then_five_final_form_failures_still_stops_at_three_calls(book, profiles, run_async):
    req, brief, plan, raw = book
    first = json.loads(json.dumps(raw))
    first["pages"][0]["sentence_units"] = ["אור", "רך"]
    for page, final, _, example, _ in FORMS:
        raw["pages"][page - 1]["sentence_units"] = [f"רועי מצא את {final} ליד {example} וחייך בשמחה.",
                                                   "החברים המשיכו יחד במסע הקסום."]
    provider = FakeProvider((plan, FakeStep(response_json=json.dumps(first)), FakeStep(response_json=json.dumps(raw))))
    result = run_async(StoryEngine(provider, profiles, settings=SETTINGS, limits=LIMITS, contract_version="2").generate(req))
    assert result.error.code == "QUALITY_REJECTED" and len(provider.calls) == 3
    assert not hasattr(result, "story")
    assert [(i.code, i.page_number) for i in result.quality.issues if i.severity != "advisory"] == [
        ("TARGET_BASE_FORM_MISSING", i) for i in range(23, 28)]
    diagnostic = export_validation_diagnostics(result.usage.attempts)[0]
    issue = diagnostic["validation_issues"][0]
    assert issue["code"] == "page_word_count" and issue["path"] == ["pages", 0]
    assert issue["observed_count"] == 2 and issue["minimum_count"] == 12 and issue["maximum_count"] == 24
