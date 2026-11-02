"""V2 schemas traverse unchanged official adapters over mock transports only."""

import json

import httpx
import pytest

from storyforge.api.configured import RuntimeConfiguration
from storyforge.domain.story_v2 import StoryPlanV2, StoryRequestV2, StoryV2
from storyforge.llm.configuration import GeminiConfig, OpenAIConfig
from storyforge.llm.fixtures_v2 import fixture_steps_v2
from storyforge.llm.gemini_provider import GeminiProvider, close_gemini_client, create_gemini_client
from storyforge.llm.openai_provider import OpenAIProvider, create_sdk_client
from storyforge.orchestration.budget import BudgetLimits, gemini_input_bound
from storyforge.orchestration.engine import StoryEngine
from storyforge.prompts.v2 import build_request_v2
from storyforge.quality.gate import assess_story
from storyforge.validation.normalization_v2 import normalize_v2
from storyforge.development.v2 import load_profiles_v2
from gemini_helpers import isolated_gemini_environment, sdk_response as gemini_response
from test_openai_provider import sdk_response as openai_response
from test_v2_execution import EXAMPLES


def roy_preflight():
    runtime = RuntimeConfiguration.model_validate_json(
        (EXAMPLES / "roy-alphabet-runtime.v2.proposed.json").read_text(encoding="utf-8"))
    req = StoryRequestV2.model_validate_json((EXAMPLES / "roy-alphabet-request.v2.he.json").read_text(encoding="utf-8"))
    brief = normalize_v2(req, load_profiles_v2(), settings=runtime.settings, page_policy=runtime.page_policy)
    return runtime, req, brief


def test_roy_configuration_and_worst_case_recovery_budget():
    runtime, _, brief = roy_preflight()
    allocation, settings = brief.execution, runtime.settings
    assert allocation.planner_output_tokens == 2792
    assert allocation.writer_output_tokens == 4128
    assert settings.max_attempts == 3 and settings.max_quality_rewrites == 1
    planner, writer = fixture_steps_v2(brief)
    plan = StoryPlanV2.model_validate_json(planner.response_json)
    story = StoryV2.model_validate_json(writer.response_json)
    report = assess_story(story, brief)
    for stage, schema, cap in (("planner", StoryPlanV2, allocation.planner_output_tokens),
                               ("writer", StoryV2, allocation.writer_output_tokens)):
        prompt = build_request_v2(stage, brief, settings.model_for(stage), cap, 45.0,
                                  plan=plan if stage == "writer" else None,
                                  draft=story if stage == "writer" else None,
                                  quality=report if stage == "writer" else None)
        assert gemini_input_bound(prompt, schema, runtime.planner.capabilities.input_overhead_tokens) <= settings.max_input_tokens
    outputs = allocation.planner_output_tokens + 2 * allocation.writer_output_tokens
    assert 3 * settings.max_input_tokens + outputs <= runtime.limits.max_total_tokens
    ceiling = runtime.planner.pricing.reservation_cost(settings.max_input_tokens, allocation.planner_output_tokens)
    ceiling += 2 * runtime.writer.pricing.reservation_cost(settings.max_input_tokens, allocation.writer_output_tokens)
    assert ceiling == pytest.approx(0.05642) and ceiling <= runtime.limits.max_cost_usd


@pytest.mark.parametrize("provider_name", ["gemini", "openai"])
@pytest.mark.parametrize("bad_first", [False, True])
def test_roy_v2_through_real_adapter_mocked_transport(run_async, profiles, provider_name, bad_first):
    runtime, req, brief = roy_preflight()
    steps = fixture_steps_v2(brief)
    seen = []
    async def perform():
        def handler(wire):
            body = json.loads(wire.content)
            planner = "offline-planner" in wire.url.path if provider_name == "gemini" else body["model"] == "offline-planner"
            seen.append(body)
            text = "{}" if bad_first and len(seen) == 1 else steps[0 if planner else 1].response_json
            response = gemini_response(text) if provider_name == "gemini" else openai_response(text)
            return httpx.Response(200, json=response)
        caps = []
        prices = []
        for stage in ("planner", "writer"):
            caps.append(runtime.planner.capabilities.model_copy(update={
                "model": f"offline-{stage}",
                "token_bound_version": "gemini-utf8-upper-v1" if provider_name == "gemini" else "openai-utf8-upper-v1"}))
            prices.append(runtime.planner.pricing.model_copy(update={"model": f"offline-{stage}", "provider": provider_name}))
        settings = runtime.settings.model_copy(update={"provider": provider_name, "planner_model": "offline-planner", "writer_model": "offline-writer"})
        transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        config_class = GeminiConfig if provider_name == "gemini" else OpenAIConfig
        config = config_class(api_key="offline-not-a-real-key", timeout_seconds=3.0)
        client = create_gemini_client(config, http_client=transport) if provider_name == "gemini" else create_sdk_client(config, http_client=transport)
        adapter = GeminiProvider if provider_name == "gemini" else OpenAIProvider
        try:
            engine = StoryEngine(adapter(client, config, tuple(caps)), profiles, settings=settings,
                                 limits=runtime.limits, capabilities=caps[0], writer_capabilities=caps[1],
                                 pricing=prices[0], writer_pricing=prices[1], contract_version="2", page_policy=runtime.page_policy)
            return await engine.generate(req)
        finally:
            if provider_name == "gemini":
                await close_gemini_client(client)
            else:
                await client.close()
            await transport.aclose()
    result = run_async(perform())
    assert result.status == "success", result
    assert len(seen) == len(result.usage.attempts) == (3 if bad_first else 2)
    assert result.story.page_count == 27 and result.quality.passed
    assert result.usage.attempts[-1].model == "offline-writer"
    assert all(a.provider == provider_name for a in result.usage.attempts)


def test_cost_admission_rejects_before_mock_sdk_call(run_async, profiles):
    runtime, req, _ = roy_preflight()
    class NeverProvider:
        provider_name = "gemini"
        async def generate(self, request, output_schema):
            raise AssertionError("Budget rejection must precede SDK invocation")
    engine = StoryEngine(NeverProvider(), profiles, settings=runtime.settings,
                         limits=BudgetLimits(max_total_tokens=111000, max_cost_usd=0.015),
                         capabilities=runtime.planner.capabilities, writer_capabilities=runtime.writer.capabilities,
                         pricing=runtime.planner.pricing, writer_pricing=runtime.writer.pricing, contract_version="2")
    result = run_async(engine.generate(req))
    assert result.status == "failure" and result.error.code == "BUDGET_EXCEEDED"
    assert not result.usage.attempts
