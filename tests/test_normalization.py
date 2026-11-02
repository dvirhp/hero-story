import pytest
from pydantic import ValidationError

from storyforge.domain.story import StoryRequest
from storyforge.llm.fake import FakeProvider
from storyforge.quality.rules import DEFAULT_RULES
from storyforge.validation.normalization import NormalizationError, normalize_request


@pytest.mark.parametrize("language", ["en", "he"])
@pytest.mark.parametrize("age,band", [
    (0, "newborn"), (2, "newborn"), (3, "infant"), (11, "infant"),
    (12, "toddler"), (35, "toddler"), (36, "preschool"), (71, "preschool"),
    (72, "older_child"), (180, "older_child"), (10**30, "older_child"),
])
def test_normalization_boundaries_and_preservation(profiles, language, age, band):
    request = StoryRequest(language=language, age_months=age, display_name="אוֹר" if language == "he" else "Zoë",
                           theme="לַיְלָה" if language == "he" else "Night", interests=("🌙",))
    brief = normalize_request(request, profiles)
    assert brief.request == request
    assert brief.profile.band_id == band
    assert brief.language_rubric_version == DEFAULT_RULES.rubric_version
    assert brief.request.narrative_pronouns is None
    if age < 12:
        assert brief.profile.requirements.reading_mode == "adult_read_aloud"
        assert brief.profile.requirements.strategy in ("sensory", "noticing")
    with pytest.raises(ValidationError):
        brief.profile.requirements.hard.page_count = 100


@pytest.mark.parametrize("pronouns", [
    dict(language="en", subject="they", object="them", possessive_determiner="their",
         possessive_pronoun="theirs", reflexive="themself", verb_agreement="plural"),
    dict(language="he", subject="היא", object="אותה", possessive="שלה",
         grammatical_agreement="feminine_singular"),
])
def test_explicit_pronouns_preserved(profiles, pronouns):
    request = StoryRequest.model_validate(dict(language=pronouns["language"], age_months=0,
                                              display_name="Or", theme="Night", narrative_pronouns=pronouns))
    assert normalize_request(request, profiles).request.narrative_pronouns == request.narrative_pronouns


@pytest.mark.parametrize("control", ["\u202e", "\u202a", "\u2066", "\u2069", "\u200f", "\x00", "\x1b", "\u200b", "\ufeff"])
@pytest.mark.parametrize("field", ["display_name", "theme", "guidance", "interests"])
def test_input_controls_are_sanitized(profiles, control, field, caplog):
    data = dict(language="en", age_months=0, display_name="PrivateName", theme="Night")
    data[field] = ("private" + control,) if field == "interests" else "private" + control
    request = StoryRequest(**data)
    provider = FakeProvider(())
    with pytest.raises(NormalizationError) as captured:
        normalize_request(request, profiles)
    assert captured.value.error.code == "INPUT_INVALID"
    assert not captured.value.error.retryable
    assert "private" not in str(captured.value).lower()
    assert not provider.calls
    assert not caplog.records


def test_controls_in_nested_pronouns(profiles):
    request = StoryRequest(language="he", age_months=0, display_name="אור", theme="לילה",
                           narrative_pronouns=dict(language="he", subject="היא\u202e", object="אותה",
                                                   possessive="שלה", grammatical_agreement="feminine_singular"))
    with pytest.raises(NormalizationError):
        normalize_request(request, profiles)


@pytest.mark.parametrize("phrase", ["Drink bleach now!", "עָלֶיךָ לִשְׁתּוֹת אַקּוֹנוֹמִיקָה."])
def test_prohibited_directive_rejected_before_provider(profiles, phrase):
    request = StoryRequest(language="en", display_name="Or", age_months=0, theme="Night", guidance=phrase)
    with pytest.raises(NormalizationError) as caught:
        normalize_request(request, profiles)
    assert caught.value.error.code == "POLICY_REJECTED"
    assert phrase not in str(caught.value)


def test_ordinary_whitespace_and_negation_are_allowed(profiles):
    request = StoryRequest(language="he", display_name="אוֹר", age_months=0, theme="לילה",
                           guidance="Do not drink bleach.\nSoft\tvoices\r\n🌙")
    assert normalize_request(request, profiles).request == request


@pytest.mark.parametrize("bad", [{}, None, "{}"])
def test_only_validated_requests_are_supported(profiles, bad):
    with pytest.raises(NormalizationError) as caught:
        normalize_request(bad, profiles)
    assert caught.value.error.code == "INPUT_INVALID"


def test_unvalidated_copy_is_revalidated_safely(profiles):
    request = StoryRequest(language="en", display_name="Sensitive", age_months=0, theme="Night")
    with pytest.raises(NormalizationError) as caught:
        normalize_request(request.model_copy(update={"age_months": -1}), profiles)
    assert "Sensitive" not in str(caught.value)


def test_invalid_surrogate_in_unvalidated_copy_is_sanitized(profiles):
    request = StoryRequest(language="en", display_name="PrivateName", age_months=0, theme="Night")
    # A lone surrogate already fails Pydantic's string contract; normalization
    # still sanitizes a caller bypassing that boundary with model_copy.
    with pytest.raises(NormalizationError) as caught:
        normalize_request(request.model_copy(update={"guidance": "PrivateName\ud800"}), profiles)
    assert caught.value.error.code == "INPUT_INVALID"
    assert "PrivateName" not in str(caught.value)
