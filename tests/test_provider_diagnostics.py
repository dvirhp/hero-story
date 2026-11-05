"""Safe diagnostics across real Gemini SDK mocks, accounting and HTTP boundaries."""

import json
import socket
import ssl

import httpx
import pytest
from pydantic import ValidationError

from storyforge.api.app import create_app
from storyforge.api.dependencies import Resources
from storyforge.domain.base import Contract
from storyforge.domain.diagnostics import ProviderDiagnostic, diagnostic_for_http
from storyforge.domain.generation import GenerationFailure, generation_result_adapter
from storyforge.llm.configuration import GeminiConfig
from storyforge.llm.gemini_provider import GeminiProvider, close_gemini_client, create_gemini_client
from storyforge.orchestration.engine import StoryEngine
from storyforge.orchestration.budget import BudgetLimits
from gemini_helpers import capabilities, exercise, isolated_gemini_environment, output_pair, sdk_response
from test_gemini_integration import runtime_configuration

PRIVATE = "private-sentinel-key-prompt-response-url-header"


@pytest.mark.parametrize("status,category", [
    (400, "invalid_request"), (401, "authentication"), (403, "permission_denied"),
    (404, "not_found"), (408, "timeout"), (409, "conflict"), (429, "rate_or_quota_limit"),
    (500, "server_error"), (502, "server_error"), (503, "server_error"), (504, "timeout"),
])
def test_sdk_http_status_preserved_without_private_diagnostics(run_async, caplog, status, category):
    def handler(request):
        return httpx.Response(status, json={"error": {"code": status, "message": PRIVATE,
                              "details": [{"private": PRIVATE}]}}, headers={"private-header": PRIVATE})
    result = run_async(exercise(handler))
    assert result.provider_diagnostic == ProviderDiagnostic(category=category, upstream_http_status=status)
    assert PRIVATE not in result.model_dump_json() + caplog.text
    assert "offline-explicit-not-a-real-key" not in result.model_dump_json() + caplog.text


@pytest.mark.parametrize("kind,category", [("connect", "connection_error"), ("dns", "dns_error"),
                                          ("tls", "tls_error"), ("read", "transport_error"),
                                          ("timeout", "timeout")])
def test_transport_types_only_no_exception_messages(run_async, caplog, kind, category):
    def handler(request):
        if kind == "timeout": raise httpx.ReadTimeout(PRIVATE, request=request)
        if kind == "read": raise httpx.ReadError(PRIVATE, request=request)
        if kind == "dns":
            try: raise socket.gaierror(PRIVATE)
            except socket.gaierror as cause: raise httpx.ConnectError(PRIVATE, request=request) from cause
        if kind == "tls":
            try: raise ssl.SSLCertVerificationError(PRIVATE)
            except ssl.SSLError as cause: raise httpx.ConnectError(PRIVATE, request=request) from cause
        raise httpx.ConnectError(PRIVATE, request=request)
    result = run_async(exercise(handler))
    assert result.provider_diagnostic == ProviderDiagnostic(category=category)
    assert result.error.retryable  # Diagnostic categories never alter policy.
    assert PRIVATE not in result.model_dump_json() + caplog.text


def test_local_configuration_failure_has_no_invented_http_status(run_async):
    def never(request): raise AssertionError("Configuration failure must precede HTTP")
    result = run_async(exercise(never, caps=capabilities("different-model")))
    assert result.error.code == "CONFIGURATION_ERROR" and not result.error.retryable
    assert result.provider_diagnostic == ProviderDiagnostic(category="configuration_error")


@pytest.mark.parametrize("path", ["/v1/stories/generate", "/v2/stories/generate"])
@pytest.mark.parametrize("kind,category,status", [("429", "rate_or_quota_limit", 429),
    ("503", "server_error", 503), ("400", "invalid_request", 400), ("403", "permission_denied", 403),
    ("404", "not_found", 404), ("transport", "connection_error", None), ("timeout", "timeout", None)])
def test_adapter_engine_http_accounting_keeps_cause_separate_from_stop(run_async, profiles, caplog, path, kind, category, status):
    calls = []
    async def perform():
        def handler(wire):
            calls.append(1)
            if kind == "transport": raise httpx.ConnectError(PRIVATE, request=wire)
            if kind == "timeout": raise httpx.ReadTimeout(PRIVATE, request=wire)
            return httpx.Response(status, json={"error": {"code": status, "message": PRIVATE}})
        runtime = runtime_configuration()
        config = GeminiConfig(api_key="offline-explicit-not-a-real-key", timeout_seconds=3.0)
        transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = create_gemini_client(config, http_client=transport)
        try:
            provider = GeminiProvider(client, config, (runtime.planner.capabilities, runtime.writer.capabilities))
            app = create_app(resources=Resources(profiles=profiles, settings=runtime.settings, limits=runtime.limits,
                pricing=runtime.planner.pricing, capabilities=runtime.planner.capabilities,
                writer_pricing=runtime.writer.pricing, writer_capabilities=runtime.writer.capabilities, provider=provider))
            body = dict(language="en", display_name="Or", age_months=0, theme="Night")
            if path.startswith("/v2"): body.update(schema_version="2", page_count=1)
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
                    return await api.post(path, json=body)
        finally:
            await close_gemini_client(client)
            await transport.aclose()
    response = run_async(perform())
    result = GenerationFailure.model_validate_json(response.content)
    terminal = kind in ("400", "403", "404")
    assert response.status_code == (500 if terminal else 503)
    assert result.error.code == ("CONFIGURATION_ERROR" if terminal else "BUDGET_EXCEEDED")
    assert result.stop_reason == ("configuration_error" if terminal else "attempt_capacity_exhausted")
    assert len(calls) == len(result.usage.attempts) == (1 if terminal else 2)
    for attempt in result.usage.attempts:
        assert attempt.provider_diagnostic == ProviderDiagnostic(category=category, upstream_http_status=status)
        assert attempt.error.code == ("CONFIGURATION_ERROR" if terminal else "DEADLINE_EXCEEDED" if kind == "timeout" else "PROVIDER_UNAVAILABLE")
        assert attempt.usage.source == "unknown" and attempt.estimated_cost_usd is None
    assert result.usage.has_unknown_usage and result.usage.has_unknown_cost
    assert result.usage.upper_estimated_cost_usd > 0
    assert PRIVATE not in response.text + caplog.text
    assert "offline-explicit-not-a-real-key" not in response.text + caplog.text


@pytest.mark.parametrize("bad", [{"category": PRIVATE}, {"category": "server_error", "message": PRIVATE},
    {"category": "server_error", "upstream_http_status": "503"},
    {"category": "server_error", "upstream_http_status": True},
    {"category": "server_error", "upstream_http_status": 600}])
def test_diagnostic_contract_rejects_free_text_extra_fields_and_coerced_status(bad):
    with pytest.raises(ValidationError): ProviderDiagnostic.model_validate(bad)


def test_forged_diagnostic_instances_are_revalidated():
    class Envelope(Contract):
        diagnostic: ProviderDiagnostic
    forged = ProviderDiagnostic(category="unknown").model_copy(update={"category": PRIVATE})
    with pytest.raises(ValidationError): Envelope(diagnostic=forged)


def test_older_saved_failure_remains_parseable_without_backfilling_upstream_status():
    raw = json.dumps(dict(status="failure", request_id="offline", total_latency_seconds=0.0,
        usage=dict(attempts=[dict(stage="planner", attempt_number=1, provider="gemini", model="offline-model",
            prompt_version="offline-v1", latency_seconds=0.0, usage=dict(source="unknown"),
            reserved_cost_usd=0.001, outcome="failure", error=dict(code="PROVIDER_UNAVAILABLE", stage="planner",
            retryable=True, message="Provider temporarily unavailable"))], known_estimated_cost_usd=0.0,
            upper_estimated_cost_usd=0.001, has_unknown_usage=True, has_unknown_cost=True),
        error=dict(code="BUDGET_EXCEEDED", stage="planner", retryable=False, message="Insufficient capacity")))
    result = generation_result_adapter.validate_json(raw)
    assert result.error.code == "BUDGET_EXCEEDED" and result.stop_reason is None
    assert len(result.usage.attempts) == 1
    assert result.usage.attempts[0].provider_diagnostic == ProviderDiagnostic(category="unknown")


def test_recovered_generation_keeps_failed_attempt_diagnostic(run_async, profiles):
    async def perform():
        request, steps = output_pair(profiles)
        calls = []
        def handler(wire):
            calls.append(1)
            if len(calls) == 1:
                return httpx.Response(429, json={"error": {"code": 429, "message": PRIVATE}})
            text = steps[0 if "offline-planner" in wire.url.path else 1].response_json
            return httpx.Response(200, json=sdk_response(text))
        runtime = runtime_configuration()
        config = GeminiConfig(api_key="offline-explicit-not-a-real-key", timeout_seconds=3.0)
        transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = create_gemini_client(config, http_client=transport)
        try:
            provider = GeminiProvider(client, config, (runtime.planner.capabilities, runtime.writer.capabilities))
            engine = StoryEngine(provider, profiles, settings=runtime.settings, limits=runtime.limits,
                pricing=runtime.planner.pricing, capabilities=runtime.planner.capabilities,
                writer_pricing=runtime.writer.pricing, writer_capabilities=runtime.writer.capabilities)
            return await engine.generate(request)
        finally:
            await close_gemini_client(client)
            await transport.aclose()
    result = run_async(perform())
    assert result.status == "success" and len(result.usage.attempts) == 3
    assert result.usage.attempts[0].provider_diagnostic == ProviderDiagnostic(category="rate_or_quota_limit", upstream_http_status=429)
    assert all(a.provider_diagnostic is None for a in result.usage.attempts[1:])
    assert PRIVATE not in result.model_dump_json()


@pytest.mark.parametrize("kind,reason", [("tokens", "token_budget_exhausted"), ("cost", "cost_budget_exhausted"),
                                       ("input", "input_capacity_exceeded")])
def test_resource_stop_reasons_are_not_provider_errors(run_async, profiles, kind, reason):
    runtime = runtime_configuration()
    class NeverProvider:
        provider_name = "gemini"
        async def generate(self, request, schema): raise AssertionError("Admission must stop without provider calls")
    limits = BudgetLimits(max_total_tokens=1 if kind == "tokens" else 33000,
                          max_cost_usd=0.000001 if kind == "cost" else 1.0)
    settings = runtime.settings.model_copy(update={"max_input_tokens": 1}) if kind == "input" else runtime.settings
    engine = StoryEngine(NeverProvider(), profiles, settings=settings, limits=limits,
        pricing=runtime.planner.pricing, capabilities=runtime.planner.capabilities,
        writer_pricing=runtime.writer.pricing, writer_capabilities=runtime.writer.capabilities)
    result = run_async(engine.generate(output_pair(profiles)[0]))
    assert result.error.code == "BUDGET_EXCEEDED" and result.stop_reason == reason
    assert not result.usage.attempts
