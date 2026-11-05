import json
import unicodedata

import pytest
from pydantic import ValidationError

from storyforge.development.models import DevelopmentConfig
from storyforge.domain.story import Story, StoryRequest
from storyforge.llm.fake import FakeProvider
from storyforge.quality.gate import assess_story
from storyforge.quality.rules import QualityRules, ScriptRule
from storyforge.validation.normalization import normalize_request


@pytest.fixture
def brief_for(profiles):
    def make(age=0, language="en", config=None, rules=None, name=None):
        request = StoryRequest(language=language, age_months=age,
                               display_name=name or ("אוֹר" if language == "he" else "Zoë"),
                               theme="לילה" if language == "he" else "Night")
        return normalize_request(request, config or profiles, **({"rules": rules} if rules else {}))
    return make


@pytest.fixture
def draft_for():
    def make(brief, count=None, word=None):
        p = brief.profile
        count = count or p.requirements.hard.words_per_page.minimum
        word = word or ("שָׁלוֹם" if brief.request.language == "he" else "soft")
        return dict(title="לילה" if brief.request.language == "he" else "Night",
                    language=brief.request.language, direction="rtl" if brief.request.language == "he" else "ltr",
                    profile_id=p.band_id, profile_version=p.version,
                    pages=[dict(page_id=f"p{i}", page_number=i,
                                text=" ".join([brief.request.display_name] + [word] * (count - 1)))
                           for i in range(1, p.requirements.hard.page_count + 1)])
    return make


def codes(report):
    return {issue.code for issue in report.issues}


@pytest.mark.parametrize("language", ["en", "he"])
@pytest.mark.parametrize("age", [0, 2, 3, 11, 12, 35, 36, 71, 72, 180])
def test_all_profiles_pass_with_repetition(brief_for, draft_for, language, age, caplog):
    brief = brief_for(age, language)
    draft = draft_for(brief)
    report = assess_story(draft, brief)
    assert report.passed
    assert all(issue.severity == "advisory" for issue in report.issues)
    assert "REPETITION_OBSERVED" in codes(report)
    assert not caplog.records
    assert draft["pages"][0]["text"].startswith(brief.request.display_name)
    assert assess_story(json.dumps(draft), brief) == report
    assert assess_story(Story.model_validate_json(json.dumps(draft)), brief) == report


@pytest.mark.parametrize("language", ["en", "he"])
@pytest.mark.parametrize("age", [0, 6, 24, 48, 120])
def test_word_and_page_boundaries(brief_for, draft_for, language, age):
    brief = brief_for(age, language)
    bounds = brief.profile.requirements.hard.words_per_page
    for count in (bounds.minimum, bounds.maximum):
        assert assess_story(draft_for(brief, count), brief).passed
    for count in (bounds.minimum - 1, bounds.maximum + 1):
        report = assess_story(draft_for(brief, count), brief)
        assert not report.passed
        assert {"PAGE_WORD_COUNT", "TOTAL_WORD_COUNT"} <= codes(report)
        assert next(i for i in report.issues if i.code == "PAGE_WORD_COUNT").page_number == 1
    for delta in (-1, 1):
        draft = draft_for(brief)
        if delta < 0:
            draft["pages"].pop()
        else:
            extra = dict(draft["pages"][-1], page_id="extra", page_number=len(draft["pages"]) + 1)
            draft["pages"].append(extra)
        assert "PAGE_COUNT_MISMATCH" in codes(assess_story(draft, brief))


@pytest.mark.parametrize("total", [29, 30, 50, 51])
def test_tighter_total_range(profiles, brief_for, draft_for, total):
    data = profiles.model_dump(mode="json")
    data["bands"][0]["languages"][0]["hard"]["total_words"] = {"minimum": 30, "maximum": 50}
    config = DevelopmentConfig.model_validate_json(json.dumps(data))
    brief = brief_for(config=config)
    draft = draft_for(brief)
    base, remainder = divmod(total, 4)
    for idx, page in enumerate(draft["pages"]):
        page["text"] = " ".join([brief.request.display_name] + ["soft"] * (base + (idx < remainder) - 1))
    report = assess_story(draft, brief)
    assert report.passed == (30 <= total <= 50)
    assert ("TOTAL_WORD_COUNT" in codes(report)) == (total in (29, 51))
    assert "PAGE_WORD_COUNT" not in codes(report)


@pytest.mark.parametrize("defect", ["direction", "order", "duplicate_id", "missing_title", "extra", "invalid_json", "wrong_type"])
def test_invalid_schema_is_safe(brief_for, draft_for, defect):
    brief = brief_for()
    draft = draft_for(brief)
    if defect == "direction":
        draft["direction"] = "rtl"
    elif defect == "order":
        draft["pages"][0]["page_number"] = 2
    elif defect == "duplicate_id":
        draft["pages"][1]["page_id"] = "p1"
    elif defect == "missing_title":
        draft.pop("title")
    elif defect == "extra":
        draft["secret"] = "PrivateSecret"
    elif defect == "invalid_json":
        draft = "not JSON PrivateSecret"
    else:
        draft = None
    report = assess_story(draft, brief)
    assert not report.passed
    assert "STORY_SCHEMA_INVALID" in codes(report)
    assert "PrivateSecret" not in report.model_dump_json()


@pytest.mark.parametrize("defect", ["language", "profile_id", "profile_version", "name"])
def test_hard_defects_repairable(brief_for, draft_for, defect):
    brief = brief_for()
    draft = draft_for(brief)
    if defect == "language":
        draft.update(language="he", direction="rtl")
    elif defect == "name":
        for page in draft["pages"]:
            page["text"] = page["text"].replace(brief.request.display_name, "soft")
    else:
        draft[defect] = "other"
    report = assess_story(draft, brief)
    expected = {"language": "LANGUAGE_METADATA_MISMATCH", "profile_id": "PROFILE_MISMATCH",
                "profile_version": "PROFILE_MISMATCH", "name": "PERSONALIZATION_MISSING"}[defect]
    assert not report.passed
    assert next(i for i in report.issues if i.code == expected).severity == "repairable"


@pytest.mark.parametrize("language,word", [("he", "hello"), ("en", "שלום")])
def test_obvious_script_mismatch(brief_for, draft_for, language, word):
    brief = brief_for(language=language)
    report = assess_story(draft_for(brief, word=word), brief)
    assert not report.passed
    assert "SCRIPT_MISMATCH" in codes(report)


@pytest.mark.parametrize("language", ["he", "en"])
def test_name_only_or_sounds_are_explicitly_inconclusive(brief_for, draft_for, language):
    brief = brief_for(language=language)
    for word in (brief.request.display_name, "♪"):
        report = assess_story(draft_for(brief, word=word), brief)
        assert report.passed
        assert "LANGUAGE_EVIDENCE_INCONCLUSIVE" in codes(report)
        assert next(i for i in report.issues if i.code == "LANGUAGE_EVIDENCE_INCONCLUSIVE").severity == "advisory"


def test_configurable_ratio_and_minimum_evidence(brief_for, draft_for):
    draft_rules = QualityRules(version="custom-v1", rubric_version="custom-language-v1",
                               scripts=(ScriptRule(language="en", minimum_letters=1, minimum_target_ratio=0.5),
                                        ScriptRule(language="he")))
    brief = brief_for(rules=draft_rules)
    draft = draft_for(brief, word="אa")
    assert assess_story(draft, brief, draft_rules).passed
    stricter = QualityRules(version="custom-v2", rubric_version="custom-language-v1",
                            scripts=(ScriptRule(language="en", minimum_letters=1, minimum_target_ratio=0.8),
                                     ScriptRule(language="he")))
    assert "SCRIPT_MISMATCH" in codes(assess_story(draft, brief, stricter))


@pytest.mark.parametrize("control", ["\u202e", "\u2068", "\u200e", "\x00", "\x1b", "\u200b"])
@pytest.mark.parametrize("location", ["title", "page", "metadata"])
def test_controls_terminal(brief_for, draft_for, control, location):
    brief = brief_for()
    draft = draft_for(brief)
    if location == "title":
        draft["title"] += control
    elif location == "metadata":
        draft["profile_id"] += control
    else:
        draft["pages"][0]["text"] += control
    report = assess_story(draft, brief)
    assert not report.passed
    issue = next(i for i in report.issues if i.code == "FORBIDDEN_UNICODE_CONTROL")
    assert issue.severity == "terminal"
    assert issue.page_number == (1 if location == "page" else None)
    assert control not in report.model_dump_json()


@pytest.mark.parametrize("phrase", ["Drink bleach now!", "עָלֶיךָ לִשְׁתּוֹת אַקּוֹנוֹמִיקָה."])
def test_prohibited_content_terminal_even_with_schema_error(brief_for, draft_for, phrase):
    brief = brief_for()
    for invalid in (False, True):
        draft = draft_for(brief)
        draft["pages"][0]["text"] += ". " + phrase
        if invalid:
            draft.pop("title")
        report = assess_story(draft, brief)
        assert not report.passed
        assert next(i for i in report.issues if i.code == "PROHIBITED_CONTENT").severity == "terminal"
        assert phrase not in report.model_dump_json()


def test_negation_and_keywords_are_not_automatically_prohibited(brief_for, draft_for):
    brief = brief_for(120)
    draft = draft_for(brief)
    draft["pages"][0]["text"] += ". Do not drink bleach. The bleach stayed locked away."
    assert "PROHIBITED_CONTENT" not in codes(assess_story(draft, brief))


def test_short_baby_refrains_have_no_plot_or_grammar_requirement(brief_for, draft_for):
    brief = brief_for(name="Alexander")
    draft = draft_for(brief)
    for page in draft["pages"]:
        page["text"] = "Alexander. La la. Sh sh."
    report = assess_story(draft, brief)
    assert report.passed
    assert {"SENTENCE_LENGTH_OBSERVATION", "REPETITION_OBSERVED", "READ_ALOUD_REVIEW"} <= codes(report)
    assert all(i.severity == "advisory" for i in report.issues)


def test_short_repeated_refrains_are_not_duplicate_page_issues(brief_for, draft_for):
    brief = brief_for(name="Alexander")
    draft = draft_for(brief)
    for page in draft["pages"]:
        page["text"] = "Alexander. La la. Sh sh."
    report = assess_story(draft, brief)
    assert report.passed
    assert "DUPLICATE_PAGE_TEXT" not in codes(report)


@pytest.mark.parametrize("language,text,repeat", [
    ("en", "Zoë and the moon say goodnight softly now.",
     "  ZOË and the moon say goodnight softly now.\n"),
    ("he", "אוֹר וְהַיָּרֵחַ אוֹמְרִים לַיְלָה טוֹב בְּשֶׁקֶט וּבְרַכּוּת עַכְשָׁיו.",
     "  אוֹר וְהַיָּרֵחַ אוֹמְרִים לַיְלָה טוֹב בְּשֶׁקֶט וּבְרַכּוּת עַכְשָׁיו.\n"),
])
def test_duplicate_substantive_page_text_is_flagged_advisory(brief_for, draft_for, language, text, repeat):
    brief = brief_for(language=language)
    draft = draft_for(brief)
    draft["pages"][0]["text"] = text
    draft["pages"][1]["text"] = repeat
    report = assess_story(draft, brief)
    assert report.passed
    issue = next(i for i in report.issues if i.code == "DUPLICATE_PAGE_TEXT")
    assert issue.severity == "advisory"
    assert issue.page_number == 2


def test_duplicate_detection_ignores_unicode_and_whitespace_variants(brief_for, draft_for):
    brief = brief_for(name="Zoë")
    draft = draft_for(brief)
    text = "Zoë and the moon say goodnight softly now."
    draft["pages"][0]["text"] = text
    # Canonical equivalence plus non-breaking spaces and a line break.
    draft["pages"][1]["text"] = " " + unicodedata.normalize("NFD", text).replace(" ", "\u00a0") + "\n"
    report = assess_story(draft, brief)
    assert report.passed
    assert next(i for i in report.issues if i.code == "DUPLICATE_PAGE_TEXT").page_number == 2


def test_varied_substantive_pages_are_not_duplicate_page_issues(brief_for, draft_for):
    brief = brief_for(name="Zoë")
    draft = draft_for(brief)
    for number, page in enumerate(draft["pages"], 1):
        page["text"] = f"Zoë watches the quiet moon rise over the sleeping garden {number}."
    report = assess_story(draft, brief)
    assert report.passed
    assert "DUPLICATE_PAGE_TEXT" not in codes(report)


def test_name_substring_is_not_personalization(brief_for, draft_for):
    brief = brief_for(name="Ann")
    draft = draft_for(brief, word="Annabelle")
    for page in draft["pages"]:
        page["text"] = page["text"].replace("Ann ", "Annabelle ")
    assert "PERSONALIZATION_MISSING" in codes(assess_story(draft, brief))


def test_no_provider_or_sensitive_logging(brief_for, draft_for, monkeypatch, caplog):
    def forbidden(*args, **kwargs):
        raise AssertionError("Provider called by pure validation")
    monkeypatch.setattr(FakeProvider, "generate", forbidden)
    brief = brief_for(name="PrivateChild")
    report = assess_story(draft_for(brief), brief)
    assert report.passed
    assert "PrivateChild" not in report.model_dump_json()
    assert not caplog.records


def test_rules_validate_supported_languages_and_thresholds():
    with pytest.raises(ValidationError):
        QualityRules(scripts=(ScriptRule(language="en"),))
    with pytest.raises(ValidationError):
        ScriptRule(language="en", minimum_target_ratio=0.0)
    with pytest.raises(ValidationError):
        ScriptRule(language="en", minimum_letters=0)


def test_rubric_mismatch_terminal(brief_for, draft_for):
    brief = brief_for()
    report = assess_story(draft_for(brief), brief, QualityRules(rubric_version="different"))
    assert not report.passed
    assert report.issues[0].code == "RUBRIC_VERSION_MISMATCH"
    assert report.issues[0].severity == "terminal"


@pytest.mark.parametrize("letters,expected", [(19, "LANGUAGE_EVIDENCE_INCONCLUSIVE"), (20, "SCRIPT_MISMATCH")])
def test_exact_script_evidence_boundary(brief_for, draft_for, letters, expected):
    brief = brief_for()
    draft = draft_for(brief, word="♪")
    draft["pages"][0]["text"] = brief.request.display_name + " " + "ש" * letters + " ♪ ♪ ♪"
    report = assess_story(draft, brief)
    assert expected in codes(report)
    assert report.passed == (letters < 20)


def test_name_cannot_supply_script_evidence(brief_for, draft_for):
    brief = brief_for(name="Alexander")
    report = assess_story(draft_for(brief, word="Alexander"), brief)
    assert "LANGUAGE_EVIDENCE_INCONCLUSIVE" in codes(report)
    assert "SCRIPT_MISMATCH" not in codes(report)


def test_hebrew_niqqud_and_order_unchanged(brief_for, draft_for):
    brief = brief_for(language="he")
    draft = draft_for(brief)
    before = json.dumps(draft, ensure_ascii=False)
    report = assess_story(draft, brief)
    assert report.passed
    assert "SCRIPT_MISMATCH" not in codes(report)
    assert json.dumps(draft, ensure_ascii=False) == before
    assert brief.request.display_name == "אוֹר"


def test_escaped_controls_and_schema_failure_stay_terminal(brief_for, draft_for):
    brief = brief_for()
    draft = draft_for(brief)
    draft["pages"][0]["text"] += "\u202e"
    draft.pop("title")
    report = assess_story(json.dumps(draft, ensure_ascii=True), brief)
    assert {"FORBIDDEN_UNICODE_CONTROL", "STORY_SCHEMA_INVALID"} <= codes(report)
    assert next(i for i in report.issues if i.code == "FORBIDDEN_UNICODE_CONTROL").severity == "terminal"


def test_unvalidated_story_copy_is_not_trusted(brief_for, draft_for):
    brief = brief_for()
    story = Story.model_validate_json(json.dumps(draft_for(brief)))
    invalid = story.model_copy(update={"direction": "rtl"})
    assert "STORY_SCHEMA_INVALID" in codes(assess_story(invalid, brief))


def test_cyclic_non_json_mapping_is_safe_schema_failure(brief_for):
    raw = {}
    raw["cycle"] = raw
    report = assess_story(raw, brief_for())
    assert not report.passed
    assert codes(report) == {"STORY_SCHEMA_INVALID"}


def test_custom_profile_changes_quality_without_orchestration(profiles, brief_for, draft_for):
    data = profiles.model_dump(mode="json")
    data["version"] = "development-v2"
    for language in data["bands"][0]["languages"]:
        language["hard"]["page_count"] = 3
        language["hard"]["total_words"] = {"minimum": 15, "maximum": 45}
    updated = DevelopmentConfig.model_validate_json(json.dumps(data))
    old_brief = brief_for()
    new_brief = brief_for(config=updated)
    assert assess_story(draft_for(new_brief), new_brief).passed
    assert old_brief.profile.requirements.hard.page_count == 4
    assert new_brief.profile.requirements.hard.page_count == 3
    report = assess_story(draft_for(new_brief), old_brief)
    assert {"PAGE_COUNT_MISMATCH", "PROFILE_MISMATCH"} <= codes(report)


def test_no_repeat_observation_is_soft(brief_for, draft_for):
    brief = brief_for()
    draft = draft_for(brief)
    for i, page in enumerate(draft["pages"]):
        page["text"] = brief.request.display_name + " " + " ".join(f"sound{i}{j}" for j in range(4))
    report = assess_story(draft, brief)
    assert report.passed
    assert "REFRAIN_REVIEW" in codes(report)
    assert next(i for i in report.issues if i.code == "REFRAIN_REVIEW").severity == "advisory"


def test_configured_directives_and_benign_emoji_sequences(brief_for, draft_for):
    rules = QualityRules(prohibited_directives=("Forbidden test sentence",))
    brief = brief_for(rules=rules)
    draft = draft_for(brief)
    draft["pages"][0]["text"] += ". Forbidden test sentence."
    assert "PROHIBITED_CONTENT" in codes(assess_story(draft, brief, rules))
    draft = draft_for(brief)
    draft["title"] = "Night 👨\u200d👩\u200d👧\u200d👦"
    assert "FORBIDDEN_UNICODE_CONTROL" not in codes(assess_story(draft, brief, rules))
