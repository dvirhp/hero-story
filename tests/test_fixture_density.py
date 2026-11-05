"""D-01 regression from Agent 4 QA 51d5f43; no live-provider conclusions."""

import json

import pytest

from storyforge.config import AppSettings
from storyforge.development.v2 import load_profiles_v2
from storyforge.domain.story_v2 import StoryRequestV2
from storyforge.llm.fixtures import LocalFixtureProvider
from storyforge.llm.fixtures_v2 import fixture_steps_v2
from storyforge.orchestration.budget import BudgetLimits
from storyforge.orchestration.engine import StoryEngine
from storyforge.quality.gate import assess_story
from storyforge.validation.normalization_v2 import normalize_v2

SETTINGS = AppSettings(planner_output_tokens=5000, writer_output_tokens=20000, max_input_tokens=64000)


def test_original_d01_feasible_request_succeeds_in_two_attempts(run_async, profiles):
    raw = dict(language="en", age_months=0, page_count=1, display_name="Or Lee", theme="Night",
               story_type="educational", structure={"targets": [{"target_id": "moon", "label": "moon"}],
               "sentence_units_per_page": {"minimum": 15, "maximum": 15}})
    request = StoryRequestV2.model_validate_json(json.dumps(raw))
    brief = normalize_v2(request, load_profiles_v2(), settings=SETTINGS)
    candidate = json.loads(fixture_steps_v2(brief)[1].response_json)
    assert len(candidate["pages"][0]["sentence_units"]) == 15
    assert sum(len(unit.split()) for unit in candidate["pages"][0]["sentence_units"]) == 15
    assert "." not in candidate["pages"][0]["sentence_units"]
    assert assess_story(candidate, brief).passed
    engine = StoryEngine(LocalFixtureProvider(), profiles, settings=SETTINGS,
                         limits=BudgetLimits(max_total_tokens=260000), contract_version="2")
    result = run_async(engine.generate(request))
    assert result.status == "success" and result.quality.passed
    assert len(result.usage.attempts) == 2


@pytest.mark.parametrize("language,name,label", [
    ("en", "Or Lee", "silver moon"), ("he", "אור לי", "ירח כסוף"),
    ("en", "Or  Lee", "silver  moon"), ("he", "אור  לי", "ירח  כסוף"),
])
@pytest.mark.parametrize("age,units", [(0, 15), (3, 20), (12, 30), (36, 45), (72, 70)])
def test_multiword_names_labels_and_exact_units_fit_unchanged_density(language, name, label, age, units):
    raw = dict(language=language, age_months=age, page_count=2, display_name=name, theme="Night",
               requested_title="Quiet", story_type="educational", structure={
               "targets": [{"target_id": f"target-{i}", "label": label} for i in range(2)],
               "sentence_units_per_page": {"minimum": units, "maximum": units}})
    brief = normalize_v2(StoryRequestV2.model_validate_json(json.dumps(raw)), load_profiles_v2(), settings=SETTINGS)
    steps = fixture_steps_v2(brief)
    assert steps == fixture_steps_v2(brief)  # deterministic
    raw_story = json.loads(steps[1].response_json)
    assert assess_story(raw_story, brief).passed
    for page in raw_story["pages"]:
        assert len(page["sentence_units"]) == units
        text = " ".join(page["sentence_units"])
        assert name in text and label in text
        assert all(unit.split() and unit.strip() != "." for unit in page["sentence_units"])
        assert brief.constraints.words_per_page.minimum <= len(text.split()) <= brief.constraints.words_per_page.maximum


@pytest.mark.parametrize("name,label", [("Or\tLee", "moon"), ("Or Lee", "silver\tmoon")])
def test_indivisible_whitespace_is_preserved_when_density_has_room(name, label):
    request = StoryRequestV2.model_validate_json(json.dumps(dict(
        language="en", display_name=name, age_months=0, theme="Night", page_count=1,
        story_type="educational", structure={"targets": [{"target_id": "moon", "label": label}],
            "sentence_units_per_page": {"minimum": 14, "maximum": 14}})))
    brief = normalize_v2(request, load_profiles_v2(), settings=SETTINGS)
    raw = json.loads(fixture_steps_v2(brief)[1].response_json)
    text = " ".join(raw["pages"][0]["sentence_units"])
    assert name in text and label in text
    assert assess_story(raw, brief).passed


def test_fixture_strategy_limit_is_an_explicit_bounded_failure(run_async, profiles):
    # This minimal fixture strategy cannot split a tab-only name gap without
    # rewriting it. It must not emit a punctuation-only entry or silently relax W.
    request = StoryRequestV2.model_validate_json(json.dumps(dict(
        language="en", display_name="Or\tLee", age_months=0, theme="Night", page_count=1,
        requested_title="Quiet", story_type="educational", structure={
            "targets": [{"target_id": "moon", "label": "moon"}],
            "sentence_units_per_page": {"minimum": 15, "maximum": 15}})))
    result = run_async(StoryEngine(LocalFixtureProvider(), profiles, settings=SETTINGS,
        limits=BudgetLimits(max_total_tokens=260000), contract_version="2").generate(request))
    assert result.status == "failure" and result.error.code == "PROVIDER_OUTPUT_INVALID"
    assert len(result.usage.attempts) == 2
