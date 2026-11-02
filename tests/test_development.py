import copy
import json

import pytest
from pydantic import ValidationError

from storyforge.development.models import DevelopmentConfig
from storyforge.development.resolver import resolve_profile


@pytest.mark.parametrize("language", ["en", "he"])
@pytest.mark.parametrize("age,band", [
    (0, "newborn"), (2, "newborn"), (3, "infant"), (11, "infant"),
    (12, "toddler"), (35, "toddler"), (36, "preschool"), (71, "preschool"),
    (72, "older_child"), (120, "older_child"), (180, "older_child"),
    (10**30, "older_child"),
])
def test_boundaries(profiles, language, age, band):
    profile = resolve_profile(profiles, age, language)
    assert profile.band_id == band
    assert profile.requirements.language == language
    assert profile.version == "development-v1"
    assert profile.provisional


@pytest.mark.parametrize("age", [-1, 1.5, True, "0", None])
def test_resolver_rejects_invalid_age(profiles, age):
    with pytest.raises(ValidationError):
        resolve_profile(profiles, age, "en")


@pytest.mark.parametrize("mutation", [
    "gap", "overlap", "start", "finite_end", "middle_open", "duplicate_id",
    "missing_language", "duplicate_language", "strategy", "word_range", "total_range",
    "page_count", "empty_bands", "extra",
])
def test_invalid_configuration(profiles, mutation):
    data = profiles.model_dump(mode="json")
    if mutation == "gap":
        data["bands"][1]["min_months"] = 4
    elif mutation == "overlap":
        data["bands"][1]["min_months"] = 2
    elif mutation == "start":
        data["bands"][0]["min_months"] = 1
    elif mutation == "finite_end":
        data["bands"][-1]["max_months"] = 240
    elif mutation == "middle_open":
        data["bands"][1]["max_months"] = None
    elif mutation == "duplicate_id":
        data["bands"][1]["band_id"] = "newborn"
    elif mutation == "missing_language":
        data["bands"][0]["languages"].pop()
    elif mutation == "duplicate_language":
        data["bands"][0]["languages"][1]["language"] = "en"
    elif mutation == "strategy":
        data["bands"][0]["languages"][0]["strategy"] = "supervisor"
    elif mutation == "word_range":
        data["bands"][0]["languages"][0]["hard"]["words_per_page"]["minimum"] = 99
    elif mutation == "total_range":
        data["bands"][0]["languages"][0]["hard"]["total_words"]["maximum"] = 999
    elif mutation == "page_count":
        data["bands"][0]["languages"][0]["hard"]["page_count"] = 0
    elif mutation == "empty_bands":
        data["bands"] = []
    else:
        data["extra"] = True
    with pytest.raises(ValidationError):
        DevelopmentConfig.model_validate_json(json.dumps(data))


def test_config_extension_and_snapshot(profiles, make_brief):
    original = make_brief(24)
    data = profiles.model_dump(mode="json")
    data["version"] = "development-v2"
    for language in data["bands"][2]["languages"]:
        language["hard"]["page_count"] = 4
        language["hard"]["total_words"] = {"minimum": 60, "maximum": 120}
    later = copy.deepcopy(data["bands"][-1])
    data["bands"][-1]["max_months"] = 144
    later.update(band_id="older_advanced", min_months=144)
    data["bands"].append(later)
    updated = DevelopmentConfig.model_validate_json(json.dumps(data))
    assert resolve_profile(updated, 180, "he").band_id == "older_advanced"
    assert make_brief(24, config=updated).profile.requirements.hard.page_count == 4
    assert original.profile.requirements.hard.page_count == 5
    with pytest.raises(ValidationError):
        original.profile.requirements.hard.page_count = 7


def test_language_specific_override(profiles):
    data = profiles.model_dump(mode="json")
    data["bands"][0]["languages"][1]["soft"]["vocabulary"] = "מילים מוכרות"
    config = DevelopmentConfig.model_validate_json(json.dumps(data))
    assert resolve_profile(config, 0, "he").requirements.soft.vocabulary == "מילים מוכרות"
    assert resolve_profile(config, 0, "en").requirements.soft.vocabulary != "מילים מוכרות"
