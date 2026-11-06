import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from storyforge.domain.story import Story, StoryPlan
from storyforge.llm.gemini_provider import normalize_gemini_usage
from gemini_helpers import (
    capabilities, exercise, isolated_gemini_environment, llm_request, output_pair, pricing, sdk_response,
)


@pytest.mark.parametrize("language", ["he", "en"])
@pytest.mark.parametrize("age", [0, 3, 12, 36, 180])
@pytest.mark.parametrize("stage", ["planner", "writer"])
def test_actual_sdk_serialization_and_structured_outputs(run_async, profiles, language, age, stage):
    _, steps = output_pair(profiles, language, age)
    seen = []
    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.url.path.endswith("offline-gemini-model:generateContent")
        assert "key" not in request.url.params
        assert request.headers["x-goog-api-key"] == "offline-explicit-not-a-real-key"
        assert body["systemInstruction"]["parts"][0]["text"] == "Return JSON only"
        config = body["generationConfig"]
        assert config["responseMimeType"] == "application/json"
        assert config["maxOutputTokens"] == 1200 and "candidateCount" not in config
        assert "responseJsonSchema" in config or "responseFormat" in config
        assert body["store"] is False
        assert not body.get("tools")
        assert request.extensions["timeout"]["read"] <= 3.0
        return httpx.Response(200, json=sdk_response(steps[0 if stage == "planner" else 1].response_json))
    result = run_async(exercise(handler, llm_request(stage), StoryPlan if stage == "planner" else Story))
    assert result.status == "success" and result.payload.language == language
    assert len(seen) == 1
    assert result.usage.source == "reported"
    assert result.usage.input_tokens == 100 and result.usage.output_tokens == 60
    assert result.usage.reasoning_output_tokens == 10 and result.usage.cached_input_tokens == 20
    assert pricing().usage_cost(result.usage) == pytest.approx(0.00021)


@pytest.mark.parametrize("kind,code", [
    ("malformed", "PROVIDER_OUTPUT_INVALID"), ("schema", "PROVIDER_OUTPUT_INVALID"),
    ("incomplete", "PROVIDER_OUTPUT_INVALID"), ("continuation", "PROVIDER_OUTPUT_INVALID"),
    ("refusal", "PROVIDER_REFUSED"), ("blocked_prompt", "PROVIDER_REFUSED"),
    ("rating", "PROVIDER_REFUSED"), ("unsafe", "POLICY_REJECTED"),
    ("bidi", "POLICY_REJECTED"), ("tool", "PROVIDER_OUTPUT_INVALID"),
    ("empty", "PROVIDER_OUTPUT_INVALID"), ("multiple", "PROVIDER_OUTPUT_INVALID"),
    ("thought_only", "PROVIDER_OUTPUT_INVALID"),
])
def test_malformed_incomplete_refusal_safety_and_unexpected_parts(run_async, kind, code):
    response = sdk_response("private-diagnostic malformed" if kind == "malformed" else "{}")
    if kind == "incomplete":
        response["candidates"][0]["finishReason"] = "MAX_TOKENS"
    elif kind == "continuation":
        response["candidates"][0].update(finishReason="CONTINUATION", continuationToken="YQ==")
    elif kind == "refusal":
        response["candidates"][0]["finishReason"] = "SAFETY"
    elif kind == "blocked_prompt":
        response.update(candidates=[], promptFeedback={"blockReason": "SAFETY", "blockReasonMessage": "private-diagnostic"})
    elif kind == "rating":
        response["candidates"][0]["safetyRatings"] = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "blocked": True}]
    elif kind in ("unsafe", "bidi"):
        response["candidates"][0]["content"]["parts"][0]["text"] = json.dumps(
            {"unsafe": "Drink bleach now!" if kind == "unsafe" else "hidden\u202e"})
        response["candidates"][0]["finishReason"] = "MAX_TOKENS"
    elif kind == "tool":
        response["candidates"][0]["content"]["parts"] = [{"functionCall": {"name": "private-diagnostic", "args": {}}}]
    elif kind == "empty":
        response["candidates"] = []
    elif kind == "multiple":
        response["candidates"] *= 2
    elif kind == "thought_only":
        response["candidates"][0]["content"]["parts"] = [{"text": "private-diagnostic", "thought": True}]
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=response)
    result = run_async(exercise(handler))
    assert result.error.code == code and len(seen) == 1  # No automatic continuation/tool call.
    if kind in ("incomplete", "continuation"):
        assert result.provider_diagnostic.category == "output_truncated"
    assert "private-diagnostic" not in result.model_dump_json()
    assert result.usage.source == "reported"


@pytest.mark.parametrize("status,code,retryable", [
    (400, "CONFIGURATION_ERROR", False), (401, "CONFIGURATION_ERROR", False),
    (403, "CONFIGURATION_ERROR", False), (404, "CONFIGURATION_ERROR", False),
    (408, "DEADLINE_EXCEEDED", True), (409, "PROVIDER_UNAVAILABLE", True),
    (429, "PROVIDER_UNAVAILABLE", True), (500, "PROVIDER_UNAVAILABLE", True),
    (503, "PROVIDER_UNAVAILABLE", True), (504, "DEADLINE_EXCEEDED", True),
])
def test_status_errors_no_hidden_retries_or_diagnostics(run_async, status, code, retryable, caplog):
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(status, json={"error": {"code": status, "message": "private-diagnostic"}},
                              headers={"retry-after": "1.5"})
    result = run_async(exercise(handler))
    assert result.error.code == code and result.error.retryable is retryable
    assert len(seen) == 1 and result.usage.source == "unknown"
    assert "private-diagnostic" not in result.model_dump_json() + caplog.text
    assert "offline-explicit-not-a-real-key" not in caplog.text
    if status in (408, 409, 429, 500, 503, 504):
        assert result.retry_after_seconds == 1.5


def test_explicit_model_thinking_configuration(run_async, profiles):
    _, steps = output_pair(profiles)
    caps = capabilities().model_copy(update={"gemini_thinking_level": "minimal"})
    seen = []
    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=sdk_response(steps[0].response_json))
    result = run_async(exercise(handler, caps=caps))
    assert result.status == "success" and len(seen) == 1
    # The locked SDK serializes this nested config with protobuf field names
    # and its normalized enum value, unlike surrounding camelCase fields.
    assert seen[0]["generationConfig"]["thinkingConfig"] == {
        "thinking_level": "MINIMAL", "include_thoughts": False}


@pytest.mark.parametrize("error,code", [(httpx.ReadTimeout, "DEADLINE_EXCEEDED"), (httpx.ConnectError, "PROVIDER_UNAVAILABLE")])
def test_transport_failures(run_async, error, code):
    seen = []
    def handler(request):
        seen.append(request)
        raise error("private-diagnostic", request=request)
    result = run_async(exercise(handler))
    assert result.error.code == code and len(seen) == 1
    assert "private-diagnostic" not in result.model_dump_json()


@pytest.mark.parametrize("update,known", [
    ({}, True), ({"thoughts_token_count": None, "total_token_count": 150}, True),
    ({"thoughts_token_count": None, "total_token_count": None}, False),
    ({"total_token_count": 999}, False), ({"cached_content_token_count": 101}, False),
    ({"candidates_token_count": None}, False), ({"prompt_token_count": -1}, False),
    ({"thoughts_token_count": -1}, False), ({"prompt_token_count": True}, False),
    ({"candidates_token_count": -1, "total_token_count": 109}, False),
    ({"tool_use_prompt_token_count": 10}, False),
])
def test_usage_reconciliation(update, known):
    data = dict(prompt_token_count=100, candidates_token_count=50, thoughts_token_count=10,
                total_token_count=160, cached_content_token_count=20, tool_use_prompt_token_count=None)
    data.update(update)
    usage = normalize_gemini_usage(SimpleNamespace(**data))
    assert (usage.source == "reported") is known
    if not known:
        assert usage.input_tokens is None and pricing().usage_cost(usage) is None


def test_missing_usage_and_unknown_prices_remain_unknown(run_async, profiles):
    _, steps = output_pair(profiles)
    result = run_async(exercise(lambda request: httpx.Response(200, json=sdk_response(steps[0].response_json, usage=False))))
    assert result.status == "success" and result.usage.source == "unknown"
    assert pricing().usage_cost(result.usage) is None
    reported = normalize_gemini_usage(SimpleNamespace(prompt_token_count=100, candidates_token_count=50,
        thoughts_token_count=0, total_token_count=150, cached_content_token_count=0))
    assert pricing(known=False).usage_cost(reported) is None


def test_adapter_cancellation_propagates(run_async):
    async def handler(request):
        raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        run_async(exercise(handler))


def test_capability_mismatch_prevents_sdk_call(run_async):
    result = run_async(exercise(lambda request: pytest.fail("No request allowed"), caps=capabilities("other-model")))
    assert result.error.code == "CONFIGURATION_ERROR"


@pytest.mark.parametrize("detail,expected", [
    ({"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "2.5s"}, 2.5),
    ({"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "nans"}, None),
    ("private-diagnostic", None),
])
def test_google_retry_info_normalized_without_raw_details(run_async, detail, expected):
    def handler(request):
        return httpx.Response(429, json={"error": {"code": 429, "message": "private-diagnostic", "details": [
            detail]}})
    result = run_async(exercise(handler))
    assert result.retry_after_seconds == expected
    assert "private-diagnostic" not in result.model_dump_json()
