import json

import pytest
from pydantic import ValidationError

from storyforge.domain.generation import GenerationError, TokenUsage
from storyforge.domain.story import StoryPlan
from storyforge.llm.fake import FakeProvider, FakeStep
from storyforge.llm.protocol import LLMRequest, LLMProvider, ProviderFailure, ProviderSuccess


def request():
    return LLMRequest(stage="planner", model="scripted-v1", prompt_version="planner-v1",
                      instructions="Return a plan", input_json="{}", max_output_tokens=1200,
                      remaining_seconds=30.0)


@pytest.mark.parametrize("language", ["he", "en"])
def test_success_and_json_validation(run_async, language):
    raw = json.dumps(dict(language=language, title_concept="לילה" if language == "he" else "Night",
                          protagonist="אור" if language == "he" else "Or", strategy="sensory",
                          pages=[dict(page_number=1, intent="קול רך" if language == "he" else "Soft sound")]))
    usage = TokenUsage(source="reported", input_tokens=100, output_tokens=40)
    provider: LLMProvider = FakeProvider((FakeStep(response_json=raw, usage=usage,
                                                latency_seconds=0.25),))
    result = run_async(provider.generate(request(), StoryPlan))
    assert isinstance(result, ProviderSuccess)
    assert result.payload.language == language
    assert result.usage == usage
    assert result.latency_seconds == 0.25
    assert len(provider.calls) == 1


@pytest.mark.parametrize("raw", ["not JSON", "{}", '{"language":"en","unexpected":1}'])
def test_malformed_output_is_sanitized(run_async, raw):
    provider = FakeProvider((FakeStep(response_json=raw),))
    result = run_async(provider.generate(request(), StoryPlan))
    assert isinstance(result, ProviderFailure)
    assert result.error.code == "PROVIDER_OUTPUT_INVALID"
    assert raw not in result.error.message
    assert result.usage.source == "unknown"
    assert result.usage.input_tokens is None
    assert len(provider.calls) == 1


@pytest.mark.parametrize("code,retryable", [
    ("PROVIDER_UNAVAILABLE", True), ("PROVIDER_REFUSED", False), ("DEADLINE_EXCEEDED", True),
])
def test_scripted_failures_no_automatic_retry(run_async, code, retryable):
    error = GenerationError(code=code, stage="planner", retryable=retryable, message="Safe error")
    provider = FakeProvider((FakeStep(error=error), FakeStep(response_json="{}")))
    result = run_async(provider.generate(request(), StoryPlan))
    assert isinstance(result, ProviderFailure)
    assert result.error == error
    assert len(provider.calls) == 1


def test_simulated_timeout_and_exhaustion(run_async):
    provider = FakeProvider((FakeStep(response_json="{}", latency_seconds=31.0),))
    result = run_async(provider.generate(request(), StoryPlan))
    assert result.error.code == "DEADLINE_EXCEEDED"
    assert result.latency_seconds == 30.0
    with pytest.raises(RuntimeError, match="script exhausted"):
        run_async(provider.generate(request(), StoryPlan))
    assert len(provider.calls) == 1


def test_script_requires_exactly_one_outcome():
    with pytest.raises(ValidationError):
        FakeStep()


@pytest.mark.parametrize("raw", ["not json", "[]", '{"a": NaN}'])
def test_request_requires_json_object(raw):
    data = request().model_dump()
    data["input_json"] = raw
    with pytest.raises(ValidationError):
        LLMRequest.model_validate(data)


def test_provider_is_deterministic(run_async):
    script = (FakeStep(response_json="{}"),)
    first, second = FakeProvider(script), FakeProvider(script)
    assert run_async(first.generate(request(), StoryPlan)) == run_async(second.generate(request(), StoryPlan))
