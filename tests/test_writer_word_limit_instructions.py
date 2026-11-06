"""Writer instructions agree with the existing joined-page whitespace counter."""

import json

import pytest

from storyforge.domain.output_validation import OutputContractError
from storyforge.domain.story_v2 import StoryV2
from storyforge.prompts.v2 import build_request_v2
from storyforge.quality.gate import assess_story
from test_roy_final_forms import book
from test_v2_execution import brief, request


@pytest.mark.parametrize("language", ["he", "en"])
@pytest.mark.parametrize("age", [0, 3, 12, 36, 72, 10000])
@pytest.mark.parametrize("density", ["light", "standard"])
def test_instruction_uses_resolved_range_for_each_language_age_density(language, age, density):
    normalized = brief(request(language, age, pages=1, text_density=density))
    limits = normalized.constraints.words_per_page
    writer = build_request_v2("writer", normalized, "scripted-v1", normalized.execution.writer_output_tokens, 45.0)
    assert writer.instructions.startswith(
        f"HARD PER-PAGE WORD LIMIT: Every page must contain {limits.minimum}-{limits.maximum} words TOTAL")
    assert "across all sentence_units" in writer.instructions
    assert "len(' '.join(sentence_units).split())" in writer.instructions
    assert "standalone Hebrew letter symbols, numbers and punctuation-only items" in writer.instructions
    assert writer.prompt_version == "writer-v2-3"
    assert writer.max_output_tokens == normalized.execution.writer_output_tokens
    assert json.loads(writer.input_json)["brief"] == normalized.model_dump(mode="json")
    planner = build_request_v2("planner", normalized, "scripted-v1", normalized.execution.planner_output_tokens, 45.0)
    assert "HARD PER-PAGE WORD LIMIT" not in planner.instructions
    assert planner.prompt_version == "planner-v2-1"


@pytest.mark.parametrize("count", [11, 12, 24, 25, 30])
def test_roy_combined_page_count_includes_symbols_numbers_punctuation_and_whitespace(book, count):
    _, normalized, _, raw = book
    prompt = build_request_v2("writer", normalized, "scripted-v1", normalized.execution.writer_output_tokens, 45.0,
                              schema_recovery=True)
    assert prompt.instructions.startswith("HARD PER-PAGE WORD LIMIT: Every page must contain 12-24 words TOTAL")
    tokens = ["\u05db", "\u05da,", "\u05de\u05dc\u05da", "7", "—", "\u05e8\u05d5\u05e2\u05d9"]
    tokens += ["\u05d0\u05d5\u05e8"] * (count - len(tokens))
    raw["pages"][22]["sentence_units"] = [" \t".join(tokens[:6]), "\n ".join(tokens[6:])]
    story = StoryV2.model_validate_json(json.dumps(raw), strict=True)
    assert len(story.pages[22].text.split()) == count
    if count in (12, 24):
        assert story.validate_for(normalized) is story
        assert assess_story(story, normalized).passed
    else:
        with pytest.raises(OutputContractError) as failure:
            story.validate_for(normalized)
        issue = failure.value.issue
        assert (issue.code, issue.path, issue.observed_count) == ("page_word_count", ("pages", 22), count)
        assert (issue.minimum_count, issue.maximum_count) == (12, 24)
