import asyncio
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from storyforge.api.app import create_app
from storyforge.api.configured import RuntimeConfiguration, StageConfiguration, create_configured_app, load_configuration
from storyforge.api.dependencies import Resources, get_provider
from storyforge.config import AppSettings
from storyforge.domain.story import StoryRequest
from storyforge.llm.fixtures import fixture_steps
from storyforge.llm.configuration import GeminiConfig
from storyforge.llm.gemini_provider import GeminiProvider, close_gemini_client, create_gemini_client
from storyforge.orchestration.budget import BudgetLimits
from storyforge.orchestration.engine import StoryEngine
from storyforge.validation.normalization import normalize_request
from gemini_helpers import capabilities, isolated_gemini_environment, output_pair, pricing, sdk_response


def runtime_configuration():
    return RuntimeConfiguration(
        settings=AppSettings(provider="gemini", planner_model="offline-planner", writer_model="offline-writer"),
        limits=BudgetLimits(max_cost_usd=1.0),
        planner=StageConfiguration(capabilities=capabilities("offline-planner"), pricing=pricing("offline-planner")),
        writer=StageConfiguration(capabilities=capabilities("offline-writer"), pricing=pricing("offline-writer", 2.0)),
    )


def engine_for(provider, profiles, runtime):
    return StoryEngine(provider, profiles, settings=runtime.settings, limits=runtime.limits,
                       capabilities=runtime.planner.capabilities, pricing=runtime.planner.pricing,
                       writer_capabilities=runtime.writer.capabilities, writer_pricing=runtime.writer.pricing)


async def execute(profiles, language="en", age=0, *, first_error=None, http=False):
    request, steps = output_pair(profiles, language, age)
    seen = []
    def handler(wire):
        seen.append(json.loads(wire.content))
        if first_error and (len(seen) == 1 or first_error in (401, 429)):
            if isinstance(first_error, int):
                return httpx.Response(first_error, json={"error": {"code": first_error, "message": "private-diagnostic"}},
                                      headers={"retry-after": "0"})
            return httpx.Response(200, json=sdk_response(first_error))
        planner = "offline-planner" in wire.url.path
        return httpx.Response(200, json=sdk_response(steps[0 if planner else 1].response_json))
    config = GeminiConfig(api_key="offline-explicit-not-a-real-key", timeout_seconds=3.0)
    transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = create_gemini_client(config, http_client=transport)
    runtime = runtime_configuration()
    provider = GeminiProvider(client, config, (runtime.planner.capabilities, runtime.writer.capabilities))
    try:
        if http:
            resources = Resources(profiles=profiles, settings=runtime.settings, limits=runtime.limits,
                                  capabilities=runtime.planner.capabilities, pricing=runtime.planner.pricing,
                                  writer_capabilities=runtime.writer.capabilities, writer_pricing=runtime.writer.pricing)
            app = create_app(resources=resources)
            app.dependency_overrides[get_provider] = lambda: provider
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
                    return await api.post("/v1/stories/generate", json=request.model_dump(mode="json")), seen
        return await engine_for(provider, profiles, runtime).generate(request), seen
    finally:
        await close_gemini_client(client)
        await transport.aclose()


@pytest.mark.parametrize("language", ["en", "he"])
@pytest.mark.parametrize("age", [0, 3, 12, 36, 180])
def test_distinct_stage_models_and_pricing_all_profiles(run_async, profiles, language, age):
    result, seen = run_async(execute(profiles, language, age))
    assert result.status == "success" and len(seen) == 2
    assert [a.model for a in result.usage.attempts] == ["offline-planner", "offline-writer"]
    assert all(a.provider == "gemini" for a in result.usage.attempts)
    assert not result.usage.has_unknown_usage and not result.usage.has_unknown_cost
    assert result.usage.known_estimated_cost_usd == pytest.approx(0.00063)


@pytest.mark.parametrize("error,calls,code", [
    (401, 1, "CONFIGURATION_ERROR"), (429, 2, "BUDGET_EXCEEDED"),
    ("private-diagnostic bad JSON", 3, None),
    ('{"unsafe":"Drink bleach now!"}', 1, "POLICY_REJECTED"),
])
def test_shared_attempt_budget_and_terminal_rules(run_async, profiles, error, calls, code):
    result, seen = run_async(execute(profiles, first_error=error))
    assert len(seen) == calls == len(result.usage.attempts)
    assert "private-diagnostic" not in result.model_dump_json()
    if code:
        assert result.error.code == code and "story" not in result.model_dump()
    else:
        assert result.status == "success"


@pytest.mark.parametrize("language", ["en", "he"])
def test_fastapi_dependency_override(run_async, profiles, language):
    response, seen = run_async(execute(profiles, language, http=True))
    assert response.status_code == 200 and len(seen) == 2
    assert response.json()["usage"]["attempts"][0]["provider"] == "gemini"


def test_explicit_configuration_reads_only_selected_key(tmp_path):
    path = tmp_path / "runtime.json"
    path.write_text(runtime_configuration().model_dump_json(), encoding="utf-8")
    class SelectedOnly(dict):
        def __getitem__(self, key):
            assert key != "OPENAI_API_KEY"
            return super().__getitem__(key)
    runtime, config = load_configuration(SelectedOnly(STORYFORGE_ALLOW_PAID_CALLS="true", STORYFORGE_CONFIG=str(path),
                                                     GEMINI_API_KEY="offline-explicit-not-a-real-key"))
    assert runtime.settings.provider == "gemini" and isinstance(config, GeminiConfig)
    assert "offline-explicit" not in repr(config) + config.model_dump_json()
    assert AppSettings().provider == "fake"


@pytest.mark.parametrize("bad_key", [None, "", "   "])
def test_missing_or_blank_key_is_sanitized(tmp_path, bad_key):
    path = tmp_path / "runtime.json"
    path.write_text(runtime_configuration().model_dump_json(), encoding="utf-8")
    values = dict(STORYFORGE_ALLOW_PAID_CALLS="true", STORYFORGE_CONFIG=str(path))
    if bad_key is not None:
        values["GEMINI_API_KEY"] = bad_key
    with pytest.raises(ValueError, match="Invalid explicit runtime configuration or credentials"):
        load_configuration(values)


def test_invalid_configuration_is_rejected():
    with pytest.raises(ValidationError):
        AppSettings(provider="gemini")
    data = runtime_configuration().model_dump(mode="json")
    data["writer"]["pricing"]["provider"] = "openai"
    with pytest.raises(ValueError, match="metadata"):
        RuntimeConfiguration.model_validate_json(json.dumps(data))


def test_configured_lifespan_has_zero_calls_and_cleans_both_pools(run_async, monkeypatch):
    runtime = runtime_configuration()
    config = GeminiConfig(api_key="offline-explicit-not-a-real-key", timeout_seconds=3.0)
    clients = []
    def factory(value):
        client = create_gemini_client(value)
        clients.append(client)
        return client
    monkeypatch.setattr("storyforge.api.configured.load_configuration", lambda env: (runtime, config))
    monkeypatch.setattr("storyforge.api.configured.create_gemini_client", factory)
    async def run():
        app = create_configured_app()
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
                assert (await api.get("/health")).status_code == 200
        assert app.state.resources is None
        # SDK has no public close-status property. Inspect pools only in this lifecycle test.
        assert clients[0]._api_client._httpx_client.is_closed
        assert clients[0]._api_client._async_httpx_client.is_closed
    run_async(run())


@pytest.mark.parametrize("mode", ["cancel", "retry_deadline", "local_timeout"])
def test_deadlines_and_cancellation_keep_ledger(run_async, profiles, mode):
    async def run():
        entered = asyncio.Event()
        seen = []
        async def handler(request):
            seen.append(request)
            entered.set()
            if mode == "retry_deadline":
                return httpx.Response(429, json={"error": {"code": 429, "message": "private"}},
                                      headers={"retry-after": "120"})
            await asyncio.Event().wait()
        runtime = runtime_configuration()
        config = GeminiConfig(api_key="offline-explicit-not-a-real-key", timeout_seconds=0.01 if mode == "local_timeout" else 3.0)
        transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = create_gemini_client(config, http_client=transport)
        provider = GeminiProvider(client, config, (runtime.planner.capabilities, runtime.writer.capabilities))
        try:
            request, _ = output_pair(profiles)
            task = asyncio.create_task(engine_for(provider, profiles, runtime).generate(request))
            await entered.wait()
            if mode == "cancel":
                task.cancel()
            result = await task
            assert result.error.code == {"cancel": "CANCELLED", "retry_deadline": "DEADLINE_EXCEEDED",
                                         "local_timeout": "BUDGET_EXCEEDED"}[mode]
            assert len(seen) == len(result.usage.attempts) == (2 if mode == "local_timeout" else 1)
            assert result.usage.has_unknown_usage and result.usage.has_unknown_cost
            assert result.usage.upper_estimated_cost_usd > 0
        finally:
            await close_gemini_client(client)
            await transport.aclose()
    run_async(run())


def test_future_writer_affordability_and_capacity_checked_before_sdk(run_async, profiles):
    class NeverCalled:
        provider_name = "gemini"
        async def generate(self, request, schema):
            pytest.fail("No SDK call allowed")
    runtime = runtime_configuration()
    data = runtime.model_dump(mode="json")
    data["limits"]["max_cost_usd"] = 0.000001
    runtime = RuntimeConfiguration.model_validate_json(json.dumps(data))
    request, _ = output_pair(profiles)
    result = run_async(engine_for(NeverCalled(), profiles, runtime).generate(request))
    assert result.error.code == "BUDGET_EXCEEDED" and not result.usage.attempts
    data["planner"]["capabilities"]["context_tokens"] = 10
    with pytest.raises(ValueError, match="capacity"):
        engine_for(NeverCalled(), profiles, RuntimeConfiguration.model_validate_json(json.dumps(data)))


@pytest.mark.parametrize("mode", ["quality_rewrite", "reported_over_cap"])
def test_quality_rewrite_and_reported_overages_obey_shared_limits(run_async, profiles, mode):
    async def run():
        request, steps = output_pair(profiles)
        seen = []
        def handler(wire):
            seen.append(wire)
            text = steps[0 if len(seen) == 1 else 1].response_json
            if mode == "quality_rewrite" and len(seen) == 2:
                body = json.loads(text)
                for page in body["pages"]:
                    page["text"] = page["text"].replace("Or", "Moon")
                text = json.dumps(body)
            response = sdk_response(text)
            if mode == "reported_over_cap":
                response["usageMetadata"].update(candidatesTokenCount=1201, thoughtsTokenCount=0, totalTokenCount=1301)
            return httpx.Response(200, json=response)
        runtime = runtime_configuration()
        config = GeminiConfig(api_key="offline-explicit-not-a-real-key", timeout_seconds=3.0)
        transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = create_gemini_client(config, http_client=transport)
        try:
            provider = GeminiProvider(client, config, (runtime.planner.capabilities, runtime.writer.capabilities))
            result = await engine_for(provider, profiles, runtime).generate(request)
            assert len(seen) == len(result.usage.attempts) == (3 if mode == "quality_rewrite" else 1)
            if mode == "quality_rewrite":
                assert result.status == "success"
                assert [a.stage for a in result.usage.attempts] == ["planner", "writer", "writer"]
            else:
                assert result.error.code == "BUDGET_EXCEEDED"
                assert result.usage.attempts[0].usage.output_tokens == 1201
        finally:
            await close_gemini_client(client)
            await transport.aclose()
    run_async(run())


def test_proposed_smoke_files_run_entire_pipeline_with_mock_transport(run_async, profiles):
    examples = Path(__file__).resolve().parents[1] / "docs" / "examples"
    runtime = RuntimeConfiguration.model_validate_json((examples / "gemini-smoke-runtime.json").read_text(encoding="utf-8"))
    request = StoryRequest.model_validate_json((examples / "gemini-smoke-request.en.json").read_text(encoding="utf-8"))
    assert request.age_months == 0
    assert runtime.limits.max_cost_usd == 0.015
    assert runtime.planner.pricing.reservation_cost(8000, 800) * 3 == pytest.approx(0.0132)
    async def run():
        steps = fixture_steps(normalize_request(request, profiles))
        seen = []
        def handler(wire):
            seen.append(wire)
            assert json.loads(wire.content)["generationConfig"]["maxOutputTokens"] == 800
            return httpx.Response(200, json=sdk_response(steps[len(seen) - 1].response_json))
        config = GeminiConfig(api_key="offline-explicit-not-a-real-key", timeout_seconds=3.0)
        transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = create_gemini_client(config, http_client=transport)
        try:
            provider = GeminiProvider(client, config, runtime.planner.capabilities)
            result = await engine_for(provider, profiles, runtime).generate(request)
            assert result.status == "success" and len(seen) == 2
            assert len(result.story.pages) == 4
            assert result.usage.upper_estimated_cost_usd < 0.015
        finally:
            await close_gemini_client(client)
            await transport.aclose()
    run_async(run())
