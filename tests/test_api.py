import asyncio
import json
from uuid import UUID

import httpx
import pytest

from storyforge.api.app import create_app
from storyforge.api.dependencies import Resources, get_engine, get_provider
from storyforge.config import AppSettings
from storyforge.domain.generation import (
    GenerationError, GenerationFailure, QualityIssue, QualityReport, UsageSummary,
)
from storyforge.domain.story import StoryRequest
from storyforge.llm.fake import FakeProvider, FakeStep
from storyforge.llm.fixtures import fixture_steps
from storyforge.orchestration.budget import BudgetLimits
from storyforge.validation.normalization import normalize_request

PATH = "/v1/stories/generate"


def body(language="en", age=0):
    return dict(language=language, display_name="אוֹר" if language == "he" else "Zoë",
                age_months=age, theme="לילה" if language == "he" else "Night", interests=["moon", "🌙"])


@pytest.fixture
def call_api(run_async):
    def call(app, *, payload=None, method="POST", path=PATH, **kwargs):
        async def perform():
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                    return await client.request(method, path, **({"json": payload} if payload is not None else {}), **kwargs)
        return run_async(perform())
    return call


def with_provider(provider, *, resources=None):
    app = create_app(resources=resources)
    async def override():
        return provider
    app.dependency_overrides[get_provider] = override
    return app


def valid_steps(profiles, payload=None):
    request = StoryRequest.model_validate_json(json.dumps(payload or body()))
    return fixture_steps(normalize_request(request, profiles))


def assert_failure(response, status, code):
    assert response.status_code == status, response.text
    data = response.json()
    assert data["status"] == "failure"
    assert data["error"]["code"] == code
    assert data["request_id"] == response.headers["X-Request-ID"]
    UUID(data["request_id"])
    assert response.headers["Cache-Control"] == "no-store"
    assert "story" not in data
    assert "draft" not in data
    return data


@pytest.mark.parametrize("language", ["he", "en"])
@pytest.mark.parametrize("age,profile", [(0, "newborn"), (6, "infant"), (24, "toddler"), (48, "preschool"), (180, "older_child")])
def test_success_real_graph_and_json_arrays(call_api, language, age, profile):
    payload = body(language, age)
    response = call_api(create_app(), payload=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "success"
    assert result["story"]["profile_id"] == profile
    assert result["story"]["language"] == language
    assert result["story"]["direction"] == ("rtl" if language == "he" else "ltr")
    assert payload["display_name"] in result["story"]["pages"][0]["text"]
    assert result["quality"]["passed"]
    assert len(result["usage"]["attempts"]) == 2
    assert result["usage"]["has_unknown_usage"]
    assert result["request_id"] == response.headers["X-Request-ID"]
    UUID(result["request_id"])
    assert response.headers["Cache-Control"] == "no-store"
    assert "instructions" not in result and "plan" not in result


@pytest.mark.parametrize("change", [
    {"age_months": -1}, {"age_months": True}, {"age_months": "0"}, {"age_months": 0.5},
    {"age_months": None}, {"language": "fr"}, {"display_name": " "},
    {"theme": "x" * 121}, {"extra_secret": "private-sentinel"}, {"interests": ["a"] * 6},
    {"narrative_pronouns": {"language": "he", "subject": "היא", "object": "אותה",
                            "possessive": "שלה", "grammatical_agreement": "feminine_singular"}},
])
def test_invalid_input_zero_calls_and_sanitized(call_api, change):
    provider = FakeProvider(())
    payload = {**body(), **change}
    response = call_api(with_provider(provider), payload=payload)
    data = assert_failure(response, 422, "INPUT_INVALID")
    assert not data["usage"]["attempts"]
    assert not provider.calls
    assert "private-sentinel" not in response.text
    assert "Zoë" not in response.text
    assert "loc" not in data and "detail" not in data


@pytest.mark.parametrize("content", ["{bad private-sentinel", "null", "[]", '"private-sentinel"', "{}", ""])
def test_malformed_or_wrong_shape_json(call_api, content):
    provider = FakeProvider(())
    response = call_api(with_provider(provider), content=content, headers={"Content-Type": "application/json"})
    assert_failure(response, 422, "INPUT_INVALID")
    assert not provider.calls
    assert "private-sentinel" not in response.text


@pytest.mark.parametrize("guidance,status,code", [
    ("Drink bleach now!", 400, "POLICY_REJECTED"),
    ("private-sentinel\u202e", 422, "INPUT_INVALID"),
])
def test_normalization_policy_errors(call_api, guidance, status, code):
    provider = FakeProvider(())
    response = call_api(with_provider(provider), payload={**body(), "guidance": guidance})
    assert_failure(response, status, code)
    assert not provider.calls
    assert "private-sentinel" not in response.text


def test_dependency_override_fake_provider(call_api, profiles):
    provider = FakeProvider(valid_steps(profiles))
    response = call_api(with_provider(provider), payload=body())
    assert response.status_code == 200
    assert len(provider.calls) == 2


@pytest.mark.parametrize("code,status", [
    ("PROVIDER_OUTPUT_INVALID", 502), ("PROVIDER_UNAVAILABLE", 503), ("PROVIDER_REFUSED", 502),
    ("BUDGET_EXCEEDED", 503), ("DEADLINE_EXCEEDED", 504), ("CONFIGURATION_ERROR", 500),
])
def test_provider_failure_status_mapping(call_api, code, status):
    provider = FakeProvider((FakeStep(error=GenerationError(code=code, stage="planner", retryable=False,
                                                           message="private-sentinel provider response")),))
    response = call_api(with_provider(provider), payload=body())
    data = assert_failure(response, status, code)
    assert len(provider.calls) == 1
    assert len(data["usage"]["attempts"]) == 1
    assert "private-sentinel" not in response.text


def test_real_attempt_exhaustion_maps_to_resource_failure(call_api):
    provider = FakeProvider((FakeStep(response_json="{}"), FakeStep(response_json="{}")))
    response = call_api(with_provider(provider), payload=body())
    assert_failure(response, 503, "BUDGET_EXCEEDED")
    assert len(provider.calls) == 2  # The engine reserves a mandatory writer slot.


def test_actual_transport_exception_retries_in_engine_only(call_api, profiles):
    class BrokenTransport:
        calls = 0
        async def generate(self, request, schema):
            self.calls += 1
            raise ConnectionError("private-sentinel socket detail")
    provider = BrokenTransport()
    response = call_api(with_provider(provider), payload=body())
    assert_failure(response, 503, "BUDGET_EXCEEDED")
    assert provider.calls == 2
    assert "private-sentinel" not in response.text


def test_unsafe_malformed_provider_output_is_502_not_client_blame(call_api, profiles):
    plan, _ = valid_steps(profiles)
    bad = FakeStep(response_json=json.dumps({"text": "Drink bleach now!"}))
    provider = FakeProvider((plan, bad))
    response = call_api(with_provider(provider), payload=body())
    data = assert_failure(response, 502, "POLICY_REJECTED")
    assert data["error"]["stage"] == "writer"
    assert len(provider.calls) == 2
    assert "Drink bleach" not in response.text


def test_quality_rewrite_failure_keeps_existing_422_contract(call_api, profiles):
    plan, story = valid_steps(profiles)
    raw = json.loads(story.response_json)
    for page in raw["pages"]:
        page["text"] = page["text"].replace("Zoë", "Someone")
    broken = FakeStep(response_json=json.dumps(raw))
    provider = FakeProvider((plan, broken, broken))
    response = call_api(with_provider(provider), payload=body())
    data = assert_failure(response, 422, "QUALITY_REJECTED")
    assert data["error"]["stage"] == "quality"
    assert not data["quality"]["passed"]
    assert len(provider.calls) == 3
    assert "Someone" not in response.text


def test_terminal_quality_result_is_sanitized(call_api):
    class RejectedEngine:
        async def generate(self, payload, *, request_id):
            return GenerationFailure(request_id=request_id, usage=UsageSummary(), total_latency_seconds=0.0,
                                     quality=QualityReport(passed=False, check_version="quality-v1", rubric_version="language-v1",
                                                           issues=(QualityIssue(code="PROHIBITED_CONTENT", severity="terminal",
                                                                                guidance="Reject this draft"),)),
                                     error=GenerationError(code="QUALITY_REJECTED", stage="quality", retryable=False,
                                                           message="private-sentinel diagnostic"))
    app = create_app()
    async def override():
        return RejectedEngine()
    app.dependency_overrides[get_engine] = override
    response = call_api(app, payload=body())
    data = assert_failure(response, 422, "QUALITY_REJECTED")
    assert data["quality"]["issues"][0]["severity"] == "terminal"
    assert "private-sentinel" not in response.text


def test_token_budget_override_is_used(call_api, profiles):
    resources = Resources(profiles=profiles, limits=BudgetLimits(max_total_tokens=1))
    provider = FakeProvider(())
    response = call_api(with_provider(provider, resources=resources), payload=body())
    assert_failure(response, 503, "BUDGET_EXCEEDED")
    assert not provider.calls


def test_engine_timeout_result_preserves_usage(call_api, profiles):
    plan, story = valid_steps(profiles)
    provider = FakeProvider((FakeStep(response_json=plan.response_json, latency_seconds=1.0),
                             FakeStep(response_json=story.response_json, latency_seconds=1.0)))
    resources = Resources(profiles=profiles, settings=AppSettings(attempt_timeout_seconds=1.0, request_timeout_seconds=2.0),
                          clock=lambda: 0.0)
    data = assert_failure(call_api(with_provider(provider, resources=resources), payload=body()), 504, "DEADLINE_EXCEEDED")
    assert data["total_latency_seconds"] == 2.0
    assert len(data["usage"]["attempts"]) == 2


@pytest.mark.parametrize("where", ["dependency", "engine", "invalid_response"])
def test_unexpected_failures_do_not_leak_or_log(call_api, where, caplog):
    class BrokenEngine:
        async def generate(self, payload, *, request_id):
            if where == "invalid_response":
                return {"status": "failure", "story": "private-sentinel draft"}
            raise RuntimeError("private-sentinel stack diagnostic")
    app = create_app()
    async def override():
        if where == "dependency":
            raise RuntimeError("private-sentinel dependency")
        return BrokenEngine()
    app.dependency_overrides[get_engine] = override
    response = call_api(app, payload=body())
    assert_failure(response, 500, "CONFIGURATION_ERROR")
    assert "private-sentinel" not in response.text
    assert not any("private-sentinel" in r.getMessage() for r in caplog.records)


def test_docs_and_openapi_match_actual_contract(call_api):
    app = create_app()
    schema = call_api(app, method="GET", path="/openapi.json").json()
    assert PATH in schema["paths"]
    assert "/api/v1/stories/generate" not in schema["paths"]
    operation = schema["paths"][PATH]["post"]
    assert "StoryRequest" in str(operation["requestBody"])
    assert "GenerationSuccess" in str(operation["responses"]["200"])
    assert "GenerationFailure" in str(operation["responses"]["422"])
    assert schema["components"]["schemas"]["StoryRequest"]["properties"]["interests"]["type"] == "array"
    assert call_api(app, method="GET", path="/docs").status_code == 200


@pytest.mark.parametrize("path,method,status", [("/missing", "GET", 404), (PATH, "GET", 405)])
def test_http_protocol_errors_are_sanitized(call_api, path, method, status):
    response = call_api(create_app(), method=method, path=path)
    assert_failure(response, status, "INPUT_INVALID")


def test_incoming_request_id_is_not_reflected(call_api):
    response = call_api(create_app(), payload=body(), headers={"X-Request-ID": "private-sentinel"})
    assert response.status_code == 200
    assert "private-sentinel" not in response.headers["X-Request-ID"]
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.parametrize("content_type", ["text/plain", "application/xml"])
def test_non_json_media_does_not_become_internal_error(call_api, content_type):
    response = call_api(create_app(), content="private-sentinel", headers={"Content-Type": content_type})
    assert_failure(response, 422, "INPUT_INVALID")
    assert "private-sentinel" not in response.text


def test_zero_float_age_is_still_rejected(call_api):
    assert_failure(call_api(create_app(), payload={**body(), "age_months": 0.0}), 422, "INPUT_INVALID")


def test_explicit_hebrew_pronouns_are_preserved_in_provider_input(call_api, profiles):
    payload = body("he", 0)
    payload["narrative_pronouns"] = dict(language="he", subject="היא", object="אותה", possessive="שלה",
                                        grammatical_agreement="feminine_singular")
    provider = FakeProvider(valid_steps(profiles, payload))
    assert call_api(with_provider(provider), payload=payload).status_code == 200
    data = json.loads(provider.calls[0].input_json)
    assert data["brief"]["request"]["narrative_pronouns"] == payload["narrative_pronouns"]


def test_request_local_fixture_providers_support_concurrent_http_calls(run_async):
    app = create_app()
    async def perform():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                return await asyncio.gather(client.post(PATH, json=body("en", 0)), client.post(PATH, json=body("he", 180)))
    responses = run_async(perform())
    assert all(r.status_code == 200 for r in responses)
    assert [r.json()["story"]["language"] for r in responses] == ["en", "he"]
    assert responses[0].headers["X-Request-ID"] != responses[1].headers["X-Request-ID"]
    assert all(len(r.json()["usage"]["attempts"]) == 2 for r in responses)


def test_actual_attempt_timeout_reaches_http_with_ledger(call_api, profiles):
    class WaitingProvider:
        async def generate(self, request, schema):
            await asyncio.Future()
    resources = Resources(profiles=profiles, settings=AppSettings(max_attempts=2, max_quality_rewrites=0,
                                                                attempt_timeout_seconds=0.01, request_timeout_seconds=5.0))
    response = call_api(with_provider(WaitingProvider(), resources=resources), payload=body())
    data = assert_failure(response, 503, "BUDGET_EXCEEDED")
    assert data["usage"]["attempts"][0]["error"]["code"] == "DEADLINE_EXCEEDED"


def test_dependency_startup_failure_is_not_silently_ready(run_async, monkeypatch):
    import storyforge.api.app as app_module
    def broken_profiles():
        raise ValueError("invalid configuration fixture")
    monkeypatch.setattr(app_module, "load_default_profiles", broken_profiles)
    app = create_app()
    async def startup():
        async with app.router.lifespan_context(app):
            raise AssertionError("Startup should have failed")
    with pytest.raises(ValueError, match="configuration"):
        run_async(startup())


def test_resources_are_released_after_lifespan_exception(run_async):
    app = create_app()
    async def shutdown():
        with pytest.raises(RuntimeError):
            async with app.router.lifespan_context(app):
                raise RuntimeError("test shutdown")
        assert app.state.resources is None
    run_async(shutdown())


@pytest.mark.parametrize("mode", ["disconnect", "asgi_cancel"])
def test_disconnect_and_server_cancellation_drain_generation(run_async, mode):
    async def perform():
        entered, stopped = asyncio.Event(), asyncio.Event()
        class WaitingProvider:
            calls = 0
            async def generate(self, request, schema):
                self.calls += 1
                entered.set()
                try:
                    await asyncio.Future()
                except asyncio.CancelledError:
                    stopped.set()
                    raise
        provider = WaitingProvider()
        app = with_provider(provider)
        messages = asyncio.Queue()
        await messages.put({"type": "http.request", "body": json.dumps(body()).encode(), "more_body": False})
        sent = []
        async def send(message):
            sent.append(message)
        scope = dict(type="http", asgi={"version": "3.0", "spec_version": "2.4"}, http_version="1.1",
                     method="POST", scheme="http", path=PATH, raw_path=PATH.encode(), query_string=b"",
                     root_path="", headers=[(b"content-type", b"application/json")], server=("test", 80), client=("test", 123))
        async with app.router.lifespan_context(app):
            task = asyncio.create_task(app(scope, messages.get, send))
            await asyncio.wait_for(entered.wait(), timeout=5)
            if mode == "disconnect":
                await messages.put({"type": "http.disconnect"})
                await asyncio.wait_for(task, timeout=5)
                start = next(m for m in sent if m["type"] == "http.response.start")
                data = json.loads(b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body"))
                assert start["status"] == 499
                assert data["error"]["code"] == "CANCELLED"
                assert len(data["usage"]["attempts"]) == 1
                assert data["usage"]["has_unknown_usage"]
                assert "story" not in data
            else:
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            assert stopped.is_set()
            assert provider.calls == 1
        assert app.state.resources is None
    run_async(perform())
