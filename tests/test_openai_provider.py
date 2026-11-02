import asyncio
import json

import httpx
import pytest

from storyforge.domain.story import Story, StoryPlan, StoryRequest
from storyforge.llm.configuration import ModelCapabilities, OpenAIConfig
from storyforge.llm.fixtures import fixture_steps
from storyforge.llm.openai_provider import OpenAIProvider, create_sdk_client
from storyforge.llm.protocol import LLMRequest
from storyforge.validation.normalization import normalize_request

MODEL = "offline-model"


@pytest.fixture
def capabilities():
    return ModelCapabilities(model=MODEL, version="offline-cap-v1", context_tokens=200000,
                             max_output_tokens=10000, input_overhead_tokens=256, structured_outputs=True)


@pytest.fixture
def output_pair(profiles):
    def make(language="en", age=0):
        request = StoryRequest(language=language, display_name="אור" if language == "he" else "Or",
                               age_months=age, theme="Night")
        return request, fixture_steps(normalize_request(request, profiles))
    return make


def llm_request(stage="planner"):
    return LLMRequest(stage=stage, model=MODEL, prompt_version="test-v1", instructions="Return JSON only",
                      input_json="{}", max_output_tokens=1200, remaining_seconds=5.0)


def sdk_response(text="{}", *, status="completed", usage=True, refusal=False):
    content = ([dict(type="refusal", refusal="private-sentinel refusal")]
               if refusal else [dict(type="output_text", text=text, annotations=[])])
    return dict(id="resp_offline", object="response", created_at=0, model=MODEL, status=status,
                error=None, incomplete_details={"reason": "max_output_tokens"} if status == "incomplete" else None,
                output=[dict(type="message", id="msg_offline", role="assistant", status="completed", content=content)],
                usage=(dict(input_tokens=100, output_tokens=50, total_tokens=150,
                            input_tokens_details={"cached_tokens": 20}, output_tokens_details={"reasoning_tokens": 10})
                       if usage else None))


async def exercise(handler, capabilities, request=None, schema=StoryPlan):
    config = OpenAIConfig(api_key="offline-test-not-a-real-key", timeout_seconds=3.0)
    client = create_sdk_client(config, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        provider = OpenAIProvider(client, config, capabilities, clock=lambda: 0.0)
        return await provider.generate(request or llm_request(), schema)
    finally:
        await client.close()


@pytest.mark.parametrize("language", ["en", "he"])
@pytest.mark.parametrize("age", [0, 180])
@pytest.mark.parametrize("stage", ["planner", "writer"])
def test_sdk_valid_structured_outputs(run_async, capabilities, output_pair, language, age, stage):
    _, steps = output_pair(language, age)
    text = steps[0 if stage == "planner" else 1].response_json
    seen = []
    def handler(request):
        seen.append(json.loads(request.content))
        assert request.url.path == "/v1/responses"
        assert request.headers["authorization"] == "Bearer offline-test-not-a-real-key"
        return httpx.Response(200, json=sdk_response(text))
    result = run_async(exercise(handler, capabilities, llm_request(stage), StoryPlan if stage == "planner" else Story))
    assert result.status == "success"
    assert result.payload.language == language
    assert result.usage.source == "reported"
    assert result.usage.input_tokens == 100 and result.usage.output_tokens == 50
    assert result.usage.cached_input_tokens == 20
    assert result.usage.reasoning_output_tokens == 10
    assert len(seen) == 1
    assert seen[0]["store"] is False and seen[0]["background"] is False
    assert seen[0]["tools"] == [] and seen[0]["max_output_tokens"] == 1200
    assert seen[0]["text"]["format"]["strict"] is True


@pytest.mark.parametrize("text,status,refusal,code", [
    ("private-sentinel malformed JSON", "completed", False, "PROVIDER_OUTPUT_INVALID"),
    ("{}", "completed", False, "PROVIDER_OUTPUT_INVALID"),
    ("{}", "incomplete", False, "PROVIDER_OUTPUT_INVALID"),
    ("{}", "completed", True, "PROVIDER_REFUSED"),
    (json.dumps({"unsafe": "Drink bleach now!"}), "incomplete", False, "POLICY_REJECTED"),
    (json.dumps({"unsafe": "hidden\u202e"}), "completed", False, "POLICY_REJECTED"),
])
def test_malformed_incomplete_refused_and_unsafe(run_async, capabilities, text, status, refusal, code):
    def handler(request):
        return httpx.Response(200, json=sdk_response(text, status=status, refusal=refusal))
    result = run_async(exercise(handler, capabilities))
    assert result.status == "failure"
    assert result.error.code == code
    assert "private-sentinel" not in result.model_dump_json()
    assert result.usage.source == "reported"
    if code in ("PROVIDER_REFUSED", "POLICY_REJECTED"):
        assert not result.error.retryable


@pytest.mark.parametrize("status,code,retryable", [
    (400, "CONFIGURATION_ERROR", False), (401, "CONFIGURATION_ERROR", False),
    (403, "CONFIGURATION_ERROR", False), (404, "CONFIGURATION_ERROR", False),
    (408, "DEADLINE_EXCEEDED", True), (409, "PROVIDER_UNAVAILABLE", True),
    (429, "PROVIDER_UNAVAILABLE", True), (500, "PROVIDER_UNAVAILABLE", True), (503, "PROVIDER_UNAVAILABLE", True),
])
def test_sdk_http_failures_never_retry_or_leak(run_async, capabilities, status, code, retryable, caplog):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"message": "private-sentinel credential detail", "type": "test_error"}},
                              headers={"retry-after": "0"})
    result = run_async(exercise(handler, capabilities))
    assert len(calls) == 1
    assert result.error.code == code and result.error.retryable == retryable
    assert result.usage.source == "unknown"
    assert result.usage.input_tokens is None
    assert "private-sentinel" not in result.model_dump_json()
    assert not any("private-sentinel" in record.getMessage() for record in caplog.records)


@pytest.mark.parametrize("failure,code", [(httpx.ConnectError, "PROVIDER_UNAVAILABLE"), (httpx.ReadTimeout, "DEADLINE_EXCEEDED")])
def test_transport_and_timeout(run_async, capabilities, failure, code):
    def handler(request):
        raise failure("private-sentinel transport", request=request)
    result = run_async(exercise(handler, capabilities))
    assert result.error.code == code
    assert result.error.retryable
    assert "private-sentinel" not in result.model_dump_json()


def test_missing_usage_remains_unknown(run_async, capabilities, output_pair):
    _, steps = output_pair()
    def handler(request):
        return httpx.Response(200, json=sdk_response(steps[0].response_json, usage=False))
    result = run_async(exercise(handler, capabilities))
    assert result.status == "success"
    assert result.usage.source == "unknown" and result.usage.input_tokens is None


def test_sdk_cancellation_propagates(run_async, capabilities):
    async def handler(request):
        raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        run_async(exercise(handler, capabilities))
