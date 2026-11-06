import json

import pytest
from pydantic import ValidationError

from storyforge.domain.generation import (
    AttemptRecord, GenerationError, GenerationFailure, GenerationSuccess, QualityIssue, QualityReport,
    TokenUsage, UsageSummary,
    generation_result_adapter,
)
from storyforge.domain.story import PageIntent, PlotElements, Story, StoryPlan, StoryRequest


@pytest.mark.parametrize("age", [-1, 0.0, 2.5, True, "0", None])
def test_strict_request_age(age):
    with pytest.raises(ValidationError):
        StoryRequest(language="en", display_name="Or", age_months=age, theme="Night")


@pytest.mark.parametrize("change", [
    {"age_months": None}, {"language": "fr"}, {"display_name": " "},
    {"theme": "x" * 121}, {"display_name": "x" * 41}, {"guidance": "x" * 501},
    {"interests": ["a"] * 6}, {"unknown": 1},
])
def test_request_bounds(change):
    data = dict(language="he", display_name="אור", age_months=0, theme="לילה")
    data.update(change)
    with pytest.raises(ValidationError):
        StoryRequest.model_validate_json(json.dumps(data))


def test_missing_age():
    with pytest.raises(ValidationError):
        StoryRequest(language="en", display_name="Or", theme="Night")


@pytest.mark.parametrize("language,pronouns", [
    ("en", {"language": "en", "subject": "they", "object": "them",
            "possessive_determiner": "their", "possessive_pronoun": "theirs",
            "reflexive": "themself", "verb_agreement": "plural"}),
    ("he", {"language": "he", "subject": "היא", "object": "אותה", "possessive": "שלה",
            "grammatical_agreement": "feminine_singular"}),
])
def test_explicit_pronouns(language, pronouns):
    data = dict(language=language, display_name="Or", age_months=0, theme="Night",
                narrative_pronouns=pronouns)
    assert StoryRequest.model_validate(data).narrative_pronouns.language == language
    data["language"] = "he" if language == "en" else "en"
    with pytest.raises(ValidationError):
        StoryRequest.model_validate(data)


def test_no_pronoun_inference():
    request = StoryRequest(language="he", display_name="שרה", age_months=0, theme="לילה")
    assert request.narrative_pronouns is None


@pytest.mark.parametrize("language", ["he", "en"])
@pytest.mark.parametrize("age", [0, 6, 24, 48, 120])
def test_profile_dependent_plan_and_story(make_brief, make_story, language, age):
    brief = make_brief(age, language)
    profile = brief.profile.requirements
    plot = (PlotElements(goal="Goal", obstacle_or_choices="Choice", resolution="Home")
            if profile.strategy in ("simple_goal", "connected_scenes") else None)
    plan = StoryPlan(language=language, title_concept="Night", protagonist=brief.request.display_name,
                     strategy=profile.strategy, plot=plot,
                     pages=tuple(PageIntent(page_number=i, intent="A gentle moment")
                                 for i in range(1, profile.hard.page_count + 1)))
    assert plan.validate_for(brief) is plan
    for words in (profile.hard.words_per_page.minimum, profile.hard.words_per_page.maximum):
        story = make_story(brief, words)
        assert story.validate_for(brief) is story
        assert Story.model_validate_json(story.model_dump_json()) == story
    for words in (profile.hard.words_per_page.minimum - 1, profile.hard.words_per_page.maximum + 1):
        with pytest.raises(ValueError):
            make_story(brief, words).validate_for(brief)
    data = make_story(brief).model_dump()
    data["pages"] = data["pages"][:-1]
    with pytest.raises(ValueError):
        Story.model_validate(data).validate_for(brief)


def test_soft_guidance_not_enforced_as_hard(make_brief, make_story):
    brief = make_brief(0, "he")
    # One long repeated utterance exceeds the soft sentence target, but obeys word bounds.
    story = make_story(brief, 15)
    assert story.validate_for(brief) is story


def test_plan_requires_plot_only_for_selected_strategies():
    common = dict(language="en", title_concept="Night", protagonist="Or",
                  pages=(PageIntent(page_number=1, intent="Gentle sounds"),))
    assert StoryPlan(**common, strategy="sensory").plot is None
    with pytest.raises(ValidationError):
        StoryPlan(**common, strategy="simple_goal")


@pytest.mark.parametrize("mutation", ["direction", "duplicate_id", "number", "profile"])
def test_story_invariants(make_brief, make_story, mutation):
    brief = make_brief()
    data = make_story(brief).model_dump(mode="json")
    if mutation == "direction":
        data["direction"] = "rtl"
    elif mutation == "duplicate_id":
        data["pages"][1]["page_id"] = data["pages"][0]["page_id"]
    elif mutation == "number":
        data["pages"][1]["page_number"] = 3
    else:
        data["profile_version"] = "different"
    with pytest.raises(ValueError):
        Story.model_validate_json(json.dumps(data)).validate_for(brief)


def test_success_requires_quality_and_failure_has_no_draft(make_brief, make_story):
    base = dict(request_id="r1", usage=UsageSummary(), total_latency_seconds=0.0)
    story = make_story(make_brief())
    report = QualityReport(passed=True, check_version="checks-v1", rubric_version="rubric-v1")
    success = GenerationSuccess(**base, story=story, quality=report)
    assert generation_result_adapter.validate_json(success.model_dump_json()) == success
    failure = GenerationFailure(**base, error=GenerationError(
        code="PROVIDER_REFUSED", stage="writer", retryable=False, message="Request refused"))
    data = failure.model_dump()
    data["story"] = story
    with pytest.raises(ValidationError):
        GenerationFailure.model_validate(data)
    with pytest.raises(ValidationError):
        QualityReport(passed=False, check_version="v1", rubric_version="v1")
    blocked = QualityReport(passed=False, check_version="v1", rubric_version="v1",
                            issues=(QualityIssue(code="LENGTH", severity="repairable", guidance="Shorten"),))
    with pytest.raises(ValidationError):
        GenerationSuccess(**base, story=story, quality=blocked)


@pytest.mark.parametrize("data", [
    {"source": "unknown", "input_tokens": 0},
    {"source": "reported", "input_tokens": 1},
    {"source": "estimated", "input_tokens": -1, "output_tokens": 2},
    {"source": "reported", "input_tokens": True, "output_tokens": 2},
])
def test_usage_does_not_coerce_or_invent_counts(data):
    with pytest.raises(ValidationError):
        TokenUsage.model_validate(data)


def test_unknown_usage_preserves_reservation():
    error = GenerationError(code="PROVIDER_UNAVAILABLE", stage="planner", retryable=True,
                            message="Provider unavailable")
    attempt = AttemptRecord(stage="planner", attempt_number=1, provider="fake", model="scripted-v1",
                            prompt_version="planner-v1", latency_seconds=0.1,
                            usage=TokenUsage(source="unknown"), reserved_cost_usd=0.02,
                            outcome="failure", error=error)
    summary = UsageSummary(attempts=(attempt,), upper_estimated_cost_usd=0.02, has_unknown_usage=True)
    assert summary.known_estimated_cost_usd == 0.0
    assert summary.attempts[0].estimated_cost_usd is None
    for change in ({"has_unknown_usage": False}, {"upper_estimated_cost_usd": 0.0},
                   {"known_estimated_cost_usd": 0.02}):
        with pytest.raises(ValidationError):
            UsageSummary.model_validate({**summary.model_dump(), **change})
    with pytest.raises(ValidationError):
        AttemptRecord.model_validate({**attempt.model_dump(), "estimated_cost_usd": 0.0})


def test_total_words_can_be_tighter_than_page_ranges(profiles, make_brief, make_story):
    from storyforge.development.models import DevelopmentConfig
    from storyforge.domain.output_validation import OutputContractError

    data = profiles.model_dump(mode="json")
    data["bands"][0]["languages"][0]["hard"]["total_words"] = {"minimum": 30, "maximum": 50}
    config = DevelopmentConfig.model_validate_json(json.dumps(data))
    brief = make_brief(config=config)
    # Five words/page fits per-page limits but 20 total violates this configuration.
    with pytest.raises(OutputContractError) as failure:
        make_story(brief, 5).validate_for(brief)
    assert failure.value.issue.code == "total_word_count"
    assert failure.value.issue.observed_count == 20
    assert make_story(brief, 10).validate_for(brief)


def test_brief_rejects_wrong_age_and_language(make_brief):
    from storyforge.domain.story import NormalizedBrief

    data = make_brief().model_dump(mode="json")
    for change in ({"age_months": 3}, {"language": "he"}):
        invalid = {**data, "request": {**data["request"], **change}}
        with pytest.raises(ValidationError):
            NormalizedBrief.model_validate_json(json.dumps(invalid))
