import asyncio
import gc

import httpx
import pytest

from storyforge.domain.story import StoryRequest
from storyforge.llm.configuration import GeminiConfig, ModelCapabilities
from storyforge.llm.fixtures import fixture_steps
from storyforge.llm.gemini_provider import GeminiProvider, close_gemini_client, create_gemini_client
from storyforge.llm.protocol import LLMRequest
from storyforge.orchestration.budget import ModelPricing
from storyforge.validation.normalization import normalize_request

MODEL = "offline-gemini-model"


@pytest.fixture(autouse=True)
def isolated_gemini_environment(monkeypatch, run_async):
    # Prevent SDK-internal ambient discovery from reading any real local keys.
    monkeypatch.setenv("GEMINI_API_KEY", "offline-ambient-not-a-real-key")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")  # Factory must override this.
    monkeypatch.setenv("GOOGLE_GEMINI_BASE_URL", "https://invalid.example")
    yield
    # SDK finalizers schedule idempotent cleanup even after explicit close.
    # Collect and drain these while the guarded loop is still running.
    async def drain_finalizers():
        gc.collect()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
    run_async(drain_finalizers())


def capabilities(model=MODEL):
    return ModelCapabilities(model=model, version="offline-gemini-cap-v1", context_tokens=200000,
                             max_output_tokens=10000, input_overhead_tokens=256, structured_outputs=True,
                             token_bound_version="gemini-utf8-upper-v1")


def pricing(model=MODEL, rate=1.0, known=True):
    return ModelPricing(provider="gemini", model=model, version="offline-gemini-prices-v1",
                        reservation_input_usd_per_million=rate, reservation_output_usd_per_million=2 * rate,
                        input_usd_per_million=rate if known else None,
                        output_usd_per_million=2 * rate if known else None,
                        cached_input_usd_per_million=rate / 2 if known else None)


def output_pair(profiles, language="en", age=0):
    request = StoryRequest(language=language, display_name="Or", age_months=age, theme="Night")
    return request, fixture_steps(normalize_request(request, profiles))


def llm_request(stage="planner", model=MODEL):
    return LLMRequest(stage=stage, model=model, prompt_version="test-v1", instructions="Return JSON only",
                      input_json="{}", max_output_tokens=1200, remaining_seconds=5.0)


def sdk_response(text="{}", *, finish="STOP", usage=True, thoughts=10):
    return dict(candidates=[dict(content=dict(role="model", parts=[dict(text=text)]), finishReason=finish)],
                usageMetadata=(dict(promptTokenCount=100, candidatesTokenCount=50, thoughtsTokenCount=thoughts,
                                    totalTokenCount=150 + thoughts, cachedContentTokenCount=20) if usage else None))


async def exercise(handler, request=None, schema=None, *, caps=None, clock=lambda: 0.0):
    from storyforge.domain.story import StoryPlan
    config = GeminiConfig(api_key="offline-explicit-not-a-real-key", timeout_seconds=3.0)
    transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = create_gemini_client(config, http_client=transport)
    try:
        provider = GeminiProvider(client, config, caps or capabilities(), clock=clock)
        return await provider.generate(request or llm_request(), schema or StoryPlan)
    finally:
        await close_gemini_client(client)
        await transport.aclose()
