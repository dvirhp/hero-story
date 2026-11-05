"""Pure quality assessment with sanitized hard failures and soft observations."""

import json
from collections import Counter
from collections.abc import Mapping
from typing import Literal

from pydantic import ValidationError

from storyforge.domain.generation import QualityIssue, QualityReport
from storyforge.domain.story import NormalizedBrief, Story
from storyforge.domain.story_v2 import NormalizedBriefV2, StoryV2
from storyforge.quality.rules import DEFAULT_RULES, QualityRules
from storyforge.quality.text import (
    contains_prohibited_directive, forbidden_controls, letter_counts, lexical_tokens,
    name_spans, normalized_comparison_text, sentences, string_values, without_name,
)

# A full page must carry enough varied prose before repeated text is treated as a
# duplicate-page signal. Short refrains, sounds and single-word patterns stay below this.
_DUPLICATE_PAGE_MIN_WORDS = 8
_DUPLICATE_PAGE_MIN_DISTINCT_TOKENS = 6


def _duplicate_page_numbers(pages) -> tuple[int, ...]:
    seen: set[str] = set()
    duplicates: list[int] = []
    for page in pages:
        text = page.text
        if (len(text.split()) < _DUPLICATE_PAGE_MIN_WORDS
                or len(set(lexical_tokens(text))) < _DUPLICATE_PAGE_MIN_DISTINCT_TOKENS):
            continue
        normalized = normalized_comparison_text(text)
        if normalized in seen:
            duplicates.append(page.page_number)
        else:
            seen.add(normalized)
    return tuple(duplicates)


def _issue(
    code: str, severity: Literal["repairable", "terminal", "advisory"],
    guidance: str, page: int | None = None,
) -> QualityIssue:
    return QualityIssue(code=code, severity=severity, guidance=guidance, page_number=page)


def _report(issues: list[QualityIssue], rules: QualityRules) -> QualityReport:
    return QualityReport(passed=not any(issue.severity != "advisory" for issue in issues),
                         issues=tuple(issues), check_version=rules.version,
                         rubric_version=rules.rubric_version)


def _text_issues(text: str, rules: QualityRules, page: int | None = None) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    if forbidden_controls(text):
        issues.append(_issue("FORBIDDEN_UNICODE_CONTROL", "terminal",
                             "Remove prohibited controls; review the rejected input before resubmission.", page))
    if contains_prohibited_directive(text, rules.prohibited_directives):
        issues.append(_issue("PROHIBITED_CONTENT", "terminal",
                             "Remove the prohibited dangerous directive; this draft cannot be repaired automatically.", page))
    return issues


def inspect_output_safety(candidate: object, rules: QualityRules = DEFAULT_RULES) -> tuple[QualityIssue, ...]:
    """Sanitized pre-schema inspection for adapters; reuse the same narrow checks."""
    raw = candidate
    if isinstance(candidate, str):
        try:
            raw = json.loads(candidate)
        except (ValueError, RecursionError):
            pass
    issues: list[QualityIssue] = []
    for value in string_values(raw):
        for issue in _text_issues(value, rules):
            if issue not in issues:
                issues.append(issue)
    return tuple(issues)


def quality_check_version(rules: QualityRules, contract_version: str) -> str:
    return f"{rules.version}+book-v2-1" if contract_version == "2" else rules.version


def assess_story(
    candidate: Story | str | Mapping[str, object], brief: NormalizedBrief | NormalizedBriefV2,
    rules: QualityRules = DEFAULT_RULES,
) -> QualityReport:
    """Accept a Story, raw JSON or JSON-compatible mapping; never return draft text.

    Input schema errors are report issues, not leaked Pydantic exceptions. A
    passing report means only that these configured deterministic checks passed.
    """
    if isinstance(brief, NormalizedBriefV2):
        rules = QualityRules.model_validate({**rules.model_dump(), "version": quality_check_version(rules, "2")})
    issues: list[QualityIssue] = []
    if brief.language_rubric_version != rules.rubric_version:
        return _report([_issue("RUBRIC_VERSION_MISMATCH", "terminal",
                               "Assess using the language rubric captured during normalization.")], rules)
    raw: object = candidate
    schema = StoryV2 if isinstance(brief, NormalizedBriefV2) else Story
    try:
        if isinstance(candidate, Story):
            raw = candidate.model_dump(warnings=False)
            story = schema.model_validate(raw)
        elif isinstance(candidate, str):
            raw = json.loads(candidate)
            story = schema.model_validate_json(candidate)
        elif isinstance(candidate, Mapping):
            raw = dict(candidate)
            story = schema.model_validate_json(json.dumps(raw, ensure_ascii=True, allow_nan=False))
        else:
            raise ValueError("unsupported story representation")
    except (ValidationError, ValueError, TypeError, RecursionError):
        # Inspect decoded values even on schema failure so unsafe text is terminal.
        for value in string_values(raw):
            for issue in _text_issues(value, rules):
                if issue not in issues:
                    issues.append(issue)
        issues.append(_issue("STORY_SCHEMA_INVALID", "repairable",
                             "Return a story matching the schema, direction, unique IDs and ordered page numbers."))
        return _report(issues, rules)

    for value in story.model_dump(exclude={"pages"}).values():
        if isinstance(value, str):
            issues.extend(_text_issues(value, rules))
    for page in story.pages:
        for value in (page.page_id, page.text):
            issues.extend(_text_issues(value, rules, page.page_number))
    for page_number in _duplicate_page_numbers(story.pages):
        issues.append(_issue("DUPLICATE_PAGE_TEXT", "advisory",
                             "Review pages that repeat the same substantive text; keep only intentional refrains or educational patterns.",
                             page_number))

    profile = brief.profile
    hard = brief.constraints if isinstance(brief, NormalizedBriefV2) else profile.requirements.hard
    if story.language != brief.request.language:
        issues.append(_issue("LANGUAGE_METADATA_MISMATCH", "repairable",
                             "Use the language and direction requested in the brief."))
    if story.profile_id != profile.band_id or story.profile_version != profile.version:
        issues.append(_issue("PROFILE_MISMATCH", "repairable",
                             "Use the profile ID and version captured in the brief."))
    if len(story.pages) != hard.page_count:
        issues.append(_issue("PAGE_COUNT_MISMATCH", "repairable",
                             "Return exactly the resolved book page count."))
    counts = tuple(len(page.text.split()) for page in story.pages)
    for page, count in zip(story.pages, counts):
        if not hard.words_per_page.minimum <= count <= hard.words_per_page.maximum:
            issues.append(_issue("PAGE_WORD_COUNT", "repairable",
                                 "Adjust this page to the profile's hard word-count range.", page.page_number))
    if not hard.total_words.minimum <= sum(counts) <= hard.total_words.maximum:
        issues.append(_issue("TOTAL_WORD_COUNT", "repairable",
                             "Adjust total page-text words to the profile's hard range; exclude the title."))
    if isinstance(brief, NormalizedBriefV2):
        if story.page_count != brief.request.page_count:
            issues.append(_issue("PAGE_COUNT_MISMATCH", "repairable", "Preserve the exact requested page count."))
        expected = hard.target_ids or (None,) * hard.page_count
        if tuple(page.target_id for page in story.pages) != expected:
            issues.append(_issue("TARGET_SEQUENCE_MISMATCH", "repairable", "Preserve one assigned target per page in requested order."))
        if brief.request.requested_title and story.title != brief.request.requested_title:
            issues.append(_issue("TITLE_MISMATCH", "repairable", "Use the exact requested title."))
        targets = {target.target_id: target for target in brief.request.structure.targets} if brief.request.structure else {}
        for page in story.pages:
            if hard.sentence_units_per_page and not hard.sentence_units_per_page.minimum <= len(page.sentence_units) <= hard.sentence_units_per_page.maximum:
                issues.append(_issue("SENTENCE_UNIT_COUNT", "repairable", "Return the requested count of sentence units.", page.page_number))
            target = targets.get(page.target_id)
            if target and not name_spans(page.text, target.label):
                issues.append(_issue("TARGET_LABEL_MISSING", "repairable", "Include the exact assigned learning label as a separate label or phrase.", page.page_number))
            if target and target.example_word and not name_spans(page.text, target.example_word):
                issues.append(_issue("TARGET_EXAMPLE_MISSING", "repairable", "Include the exact supplied example word.", page.page_number))
            if target and target.base_form and not name_spans(page.text, target.base_form):
                issues.append(_issue("TARGET_BASE_FORM_MISSING", "repairable", "Include the supplied base form in the explanation.", page.page_number))
        if len(story.pages) > 1 and len({page.text for page in story.pages}) * 2 <= len(story.pages):
            issues.append(_issue("FORMULAIC_PAGE_REPETITION", "advisory", "Review repeated whole pages against age-appropriate refrain and narrative-variety guidance."))
        issues.append(_issue("NARRATIVE_COVERAGE_REVIEW", "advisory", "Review active agency, meaningful progression, sentence grammar and educational accuracy; target metadata alone cannot prove them."))
    if not any(name_spans(text, brief.request.display_name)
               for text in (story.title, *(page.text for page in story.pages))):
        issues.append(_issue("PERSONALIZATION_MISSING", "repairable",
                             "Include the exact supplied display name at least once as a complete name."))

    body = "\n".join(without_name(page.text, brief.request.display_name) for page in story.pages)
    script = next(rule for rule in rules.scripts if rule.language == brief.request.language)
    matching, eligible = letter_counts(body, brief.request.language)
    if eligible < script.minimum_letters:
        issues.append(_issue("LANGUAGE_EVIDENCE_INCONCLUSIVE", "advisory",
                             "Too few eligible letters to assess script; review language manually. This observation does not block acceptance."))
    elif matching / eligible < script.minimum_target_ratio:
        issues.append(_issue("SCRIPT_MISMATCH", "repairable",
                             "Use the requested language's script in the story body; preserve the child's name."))

    soft = profile.requirements.soft
    for page in story.pages:
        lengths = tuple(len(sentence.split()) for sentence in sentences(page.text))
        if any(not soft.sentence_words.minimum <= count <= soft.sentence_words.maximum for count in lengths):
            issues.append(_issue("SENTENCE_LENGTH_OBSERVATION", "advisory",
                                 "Review sentence/utterance lengths against the profile's soft target; punctuation-based counts are approximate.", page.page_number))
    tokens = lexical_tokens(body)
    issues.append(_issue("VOCABULARY_FORM_COUNT", "advisory",
                         f"Body excluding the supplied name contains {len(set(tokens))} distinct word forms across {len(tokens)} tokens; this does not measure reading difficulty."))
    if any(count > 1 for count in Counter(tokens).values()):
        issues.append(_issue("REPETITION_OBSERVED", "advisory",
                             "Repeated tokens were observed; compare with the profile's refrain guidance. Intentional repetition is allowed."))
    else:
        issues.append(_issue("REFRAIN_REVIEW", "advisory",
                             "No repeated tokens were observed; review the profile's optional or suggested refrain guidance manually."))
    issues.append(_issue("VOCABULARY_NARRATIVE_REVIEW", "advisory",
                         "Review vocabulary and narrative against the captured profile guidance; word counts cannot establish their suitability."))
    if profile.requirements.reading_mode == "adult_read_aloud":
        issues.append(_issue("READ_ALOUD_REVIEW", "advisory",
                             "Review aloud for rhythm and reassuring sensory flow; a conflict or traditional plot is not required by sensory profiles."))
    return _report(issues, rules)
