import json

import pytest
from pydantic import ValidationError

from storyforge.config import AppSettings
from storyforge.development.v2 import DevelopmentProfilesV2, load_profiles_v2, resolve_v2
from storyforge.domain.story_v2 import EducationalTarget, OrderedTargets, StoryRequestV2
from storyforge.validation.normalization import NormalizationError
from storyforge.validation.normalization_v2 import normalize_v2
from storyforge.validation.page_policy import PagePolicy


def request(**changes):
    return StoryRequestV2(language="en", display_name="Or", age_months=0, theme="Night", page_count=4, **changes)


@pytest.mark.parametrize("value", [None, True, False, 0, -1, 2.5, "27", "auto"])
def test_explicit_strict_pages_no_automatic_mode(value):
    with pytest.raises(ValidationError):
        StoryRequestV2(language="he", display_name="Or", age_months=36, theme="Night", page_count=value)


@pytest.mark.parametrize("language", ["en", "he"])
@pytest.mark.parametrize("age", [0, 2, 3, 11, 12, 35, 36, 71, 72, 180, 10000])
@pytest.mark.parametrize("pages", [1, 6, 27, 32])
def test_requested_count_is_independent_of_age(language, age, pages):
    req = StoryRequestV2(language=language, display_name="Or", age_months=age, theme="Night", page_count=pages)
    brief = normalize_v2(req, load_profiles_v2(), settings=AppSettings(planner_output_tokens=5000, writer_output_tokens=20000))
    assert brief.constraints.page_count == pages
    assert brief.constraints.total_words.minimum == pages * brief.constraints.words_per_page.minimum
    snapshot = brief.profile.model_dump_json()
    assert "page_count" not in snapshot and "total_words" not in snapshot


def test_service_page_limit_is_configurable_and_never_clamped():
    req = StoryRequestV2(language="en", display_name="Or", age_months=0, theme="Night", page_count=40)
    with pytest.raises(NormalizationError) as error:
        normalize_v2(req, load_profiles_v2())
    assert error.value.error.code == "INPUT_INVALID"
    brief = normalize_v2(req, load_profiles_v2(), page_policy=PagePolicy(maximum_pages=40),
                         settings=AppSettings(planner_output_tokens=5000, writer_output_tokens=10000))
    assert brief.request.page_count == 40
    with pytest.raises(ValidationError):
        PagePolicy(minimum_pages=5, maximum_pages=2)


def test_missing_page_count_is_not_inferred_from_age():
    with pytest.raises(ValidationError):
        StoryRequestV2(language="en", display_name="Or", age_months=36, theme="Night")


def test_density_changes_text_not_book_length():
    settings = AppSettings(planner_output_tokens=5000, writer_output_tokens=10000)
    kwargs = dict(language="he", display_name="Or", age_months=36, theme="Night", page_count=27)
    profiles = load_profiles_v2()
    light = normalize_v2(StoryRequestV2(**kwargs, text_density="light"), profiles, settings=settings)
    standard = normalize_v2(StoryRequestV2(**kwargs), profiles, settings=settings)
    assert light.constraints.page_count == standard.constraints.page_count == 27
    assert light.constraints.words_per_page.minimum == 12
    assert standard.constraints.words_per_page.minimum == 25


def test_insufficient_output_capacity_fails_without_reducing_pages():
    req = StoryRequestV2(language="he", display_name="Or", age_months=180, theme="Night", page_count=32)
    with pytest.raises(NormalizationError) as error:
        normalize_v2(req, load_profiles_v2())
    assert error.value.error.code == "BUDGET_EXCEEDED" and req.page_count == 32


def test_structured_targets_require_exact_coverage_and_unique_ids():
    target = EducationalTarget(target_id="t1", label="A", kind="letter")
    with pytest.raises(ValidationError):
        OrderedTargets(targets=(target, target))
    with pytest.raises(ValidationError):
        StoryRequestV2(language="en", display_name="Or", age_months=36, theme="Letters", page_count=2,
                       story_type="alphabet", structure=OrderedTargets(targets=(target,)))
    with pytest.raises(ValidationError):
        request(story_type="alphabet")


def test_general_final_form_contract_has_no_hebrew_dependency():
    final = EducationalTarget(target_id="final", label="z", kind="letter", base_form="a", example_word="fizz")
    structure = OrderedTargets(targets=(EducationalTarget(target_id="base", label="a", kind="letter"), final))
    req = StoryRequestV2(language="en", display_name="Or", age_months=36, theme="Symbols", page_count=2,
                         story_type="alphabet", structure=structure)
    assert req.structure.targets[1].example_word.endswith("z")
    with pytest.raises(ValidationError):
        EducationalTarget(target_id="bad", label="z", kind="letter", base_form="a", example_word="tree")


def test_new_profiles_reject_age_owned_page_counts_and_invalid_coverage():
    data = load_profiles_v2().model_dump(mode="json")
    data["bands"][0]["languages"][0]["page_count"] = 4
    with pytest.raises(ValidationError):
        DevelopmentProfilesV2.model_validate_json(json.dumps(data))
    data = load_profiles_v2().model_dump(mode="json")
    data["bands"][0]["min_months"] = 1
    with pytest.raises(ValidationError):
        DevelopmentProfilesV2.model_validate_json(json.dumps(data))
    with pytest.raises(ValidationError):
        resolve_v2(load_profiles_v2(), True, "en")
