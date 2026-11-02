import asyncio
import json

import httpx
import pytest

from storyforge.api.app import create_app
from storyforge.api.configured import RuntimeConfiguration, StageConfiguration, create_configured_app, load_configuration
from storyforge.api.dependencies import Resources, get_provider
from storyforge.config import AppSettings
from storyforge.domain.story import StoryRequest
from storyforge.llm.configuration import ModelCapabilities, OpenAIConfig
from storyforge.llm.fixtures import fixture_steps
from storyforge.llm.openai_provider import OpenAIProvider, create_sdk_client
from storyforge.orchestration.budget import BudgetLimits, ModelPricing
from storyforge.orchestration.engine import StoryEngine
from storyforge.validation.normalization import normalize_request
from test_openai_provider import sdk_response


def metadata(model, rate=1.0):
    return (
        ModelCapabilities(model=model, version="offline-cap-v1", context_tokens=200000,
                          max_output_tokens=10000, input_overhead_tokens=256, structured_outputs=True),
        ModelPricing(model=model, version="offline-prices-v1", reservation_input_usd_per_million=rate,
                     reservation_output_usd_per_million=rate),
    )


async def execute(profiles, language="en", age=0, *, failure=None, http=False):
    request = StoryRequest(language=language, display_name="Or", age_months=age, theme="Night")
    steps = fixture_steps(normalize_request(request, profiles))
    seen = []

    def handler(wire):
        body = json.loads(wire.content)
        seen.append(body)
        if failure and (len(seen) == 1 or failure in (401, 429)):
            if isinstance(failure, int):
                return httpx.Response(failure, json={"error": {"message": "private-diagnostic"}},
                                      headers={"Retry-After": "0"})
            return httpx.Response(200, json=sdk_response(failure))
        text = steps[0 if body["model"] == "offline-planner" else 1].response_json
        return httpx.Response(200, json=sdk_response(text))

    config = OpenAIConfig(api_key="offline-test-not-a-real-key", timeout_seconds=3.0)
    client = create_sdk_client(config, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    planner, planner_price = metadata("offline-planner")
    writer, writer_price = metadata("offline-writer", 2.0)
    settings = AppSettings(provider="openai", planner_model=planner.model, writer_model=writer.model)
    limits = BudgetLimits(max_cost_usd=1.0)
    provider = OpenAIProvider(client, config, (planner, writer))
    resources = Resources(profiles=profiles, settings=settings, limits=limits, pricing=planner_price,
                          capabilities=planner, writer_pricing=writer_price, writer_capabilities=writer)
    try:
        if http:
            app = create_app(resources=resources)
            app.dependency_overrides[get_provider] = lambda: provider
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
                    response = await api.post("/v1/stories/generate", json=request.model_dump(mode="json"))
                    return response, seen
        engine = StoryEngine(provider, profiles, settings=settings, limits=limits, pricing=planner_price,
                             capabilities=planner, writer_pricing=writer_price, writer_capabilities=writer)
        return await engine.generate(request), seen
    finally:
        await client.close()


@pytest.mark.parametrize("language", ["en", "he"])
@pytest.mark.parametrize("age", [0, 3, 12, 36, 180])
def test_separate_stage_models_all_profiles(run_async, profiles, language, age):
    result, seen = run_async(execute(profiles, language, age))
    assert result.status == "success"
    assert [item["model"] for item in seen] == ["offline-planner", "offline-writer"]
    assert len(result.usage.attempts) == 2
    assert result.usage.has_unknown_cost and not result.usage.has_unknown_usage
    assert result.usage.known_estimated_cost_usd == 0.0
    assert result.usage.attempts[1].reserved_cost_usd > result.usage.attempts[0].reserved_cost_usd


@pytest.mark.parametrize("failure,calls,code", [
    (401, 1, "CONFIGURATION_ERROR"), (429, 2, "BUDGET_EXCEEDED"),
    ("private-diagnostic malformed", 3, None),
    ('{"unsafe":"Drink bleach now!"}', 1, "POLICY_REJECTED"),
])
def test_graph_retry_and_terminal_rules(run_async, profiles, failure, calls, code):
    result, seen = run_async(execute(profiles, failure=failure))
    assert len(seen) == calls == len(result.usage.attempts)
    if code:
        assert result.error.code == code
        assert "story" not in result.model_dump()
    else:
        assert result.status == "success"
    assert "private-diagnostic" not in result.model_dump_json()


@pytest.mark.parametrize("language", ["he", "en"])
def test_http_override_real_adapter_mocked_transport(run_async, profiles, language):
    response, seen = run_async(execute(profiles, language, http=True))
    assert response.status_code == 200
    assert response.json()["usage"]["has_unknown_cost"] is True
    assert len(seen) == 2


def test_explicit_opt_in_before_any_key_lookup():
    class NoCredentials(dict):
        def __getitem__(self, key):
            raise AssertionError("No configuration/credential lookup allowed")
    with pytest.raises(ValueError, match="opt-in"):
        load_configuration(NoCredentials())


def test_capacity_and_stage_metadata_rejected_before_calls(profiles):
    cap, price = metadata("offline-planner")
    settings = AppSettings(provider="openai", model=cap.model)
    with pytest.raises(ValueError, match="capacity"):
        StoryEngine(object(), profiles, settings=settings, limits=BudgetLimits(max_cost_usd=1.0),
                    capabilities=cap.model_copy(update={"context_tokens": 10}), pricing=price)
    with pytest.raises(ValueError, match="metadata"):
        RuntimeConfiguration(settings=settings, limits=BudgetLimits(max_cost_usd=1.0),
                             planner={"capabilities": cap, "pricing": price},
                             writer={"capabilities": cap, "pricing": metadata("different")[1]})


def test_retry_after_deadline_prevents_extra_call(run_async, profiles):
    async def run():
        count = 0
        def handler(request):
            nonlocal count
            count += 1
            return httpx.Response(429, json={"error": {"message": "private"}}, headers={"retry-after": "120"})
        config = OpenAIConfig(api_key="offline-test-not-a-real-key", timeout_seconds=3.0)
        client = create_sdk_client(config, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        cap, price = metadata("offline-model")
        try:
            engine = StoryEngine(OpenAIProvider(client, config, cap), profiles,
                                 settings=AppSettings(provider="openai", model=cap.model),
                                 limits=BudgetLimits(max_cost_usd=1.0), capabilities=cap, pricing=price)
            result = await engine.generate(StoryRequest(language="en", display_name="Or", age_months=0, theme="Night"))
            assert count == 1 and len(result.usage.attempts) == 1
            assert result.error.code == "DEADLINE_EXCEEDED"
        finally:
            await client.close()
    run_async(run())


def test_configured_lifespan_does_not_call_provider_and_closes_pool(run_async, monkeypatch):
    cap, price = metadata("offline-model")
    runtime = RuntimeConfiguration(settings=AppSettings(provider="openai", model=cap.model),
                                   limits=BudgetLimits(max_cost_usd=1.0),
                                   planner=StageConfiguration(capabilities=cap, pricing=price),
                                   writer=StageConfiguration(capabilities=cap, pricing=price))
    config = OpenAIConfig(api_key="offline-test-not-a-real-key", timeout_seconds=3.0)
    client = create_sdk_client(config, http_client=httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: pytest.fail("Startup made a provider call"))))
    monkeypatch.setattr("storyforge.api.configured.load_configuration", lambda env: (runtime, config))
    monkeypatch.setattr("storyforge.api.configured.create_sdk_client", lambda value: client)
    async def run():
        app = create_configured_app()
        assert not client.is_closed()
        async with app.router.lifespan_context(app):
            assert app.state.resources.settings.provider == "openai"
        assert client.is_closed() and app.state.resources is None
    run_async(run())


def test_real_adapter_cancellation_preserves_ledger(run_async, profiles):
    async def run():
        entered = asyncio.Event()
        async def handler(request):
            entered.set()
            await asyncio.Event().wait()
        config = OpenAIConfig(api_key="offline-test-not-a-real-key", timeout_seconds=3.0)
        client = create_sdk_client(config, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        cap, price = metadata("offline-model")
        try:
            engine = StoryEngine(OpenAIProvider(client, config, cap), profiles,
                                 settings=AppSettings(provider="openai", model=cap.model),
                                 limits=BudgetLimits(max_cost_usd=1.0), capabilities=cap, pricing=price)
            task = asyncio.create_task(engine.generate(StoryRequest(language="en", display_name="Or", age_months=0, theme="Night")))
            await entered.wait()
            task.cancel()
            result = await task
            assert result.error.code == "CANCELLED"
            assert len(result.usage.attempts) == 1
            assert result.usage.has_unknown_usage and result.usage.has_unknown_cost
            assert result.usage.upper_estimated_cost_usd > 0
        finally:
            await client.close()
    run_async(run())


def test_future_writer_price_reserved_before_planner(run_async, profiles):
    cap, price = metadata("offline-model")
    class NeverCalled:
        provider_name = "openai"
        async def generate(self, request, schema):
            pytest.fail("Unaffordable writer must prevent planner call")
    engine = StoryEngine(NeverCalled(), profiles, settings=AppSettings(provider="openai", model=cap.model),
                         limits=BudgetLimits(max_cost_usd=0.02), capabilities=cap, pricing=price,
                         writer_pricing=metadata(cap.model, 100.0)[1])
    result = run_async(engine.generate(StoryRequest(language="en", display_name="Or", age_months=0, theme="Night")))
    assert result.error.code == "BUDGET_EXCEEDED" and not result.usage.attempts


def test_real_settings_never_silently_fall_back_to_fake(run_async, profiles):
    async def run():
        app = create_app(resources=Resources(profiles=profiles, settings=AppSettings(provider="openai", model="offline-model")))
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
                response = await api.post("/v1/stories/generate", json={
                    "language": "en", "display_name": "Or", "age_months": 0, "theme": "Night"})
                assert response.status_code == 500
                assert response.json()["error"]["code"] == "CONFIGURATION_ERROR"
                assert not response.json()["usage"]["attempts"]
    run_async(run())
