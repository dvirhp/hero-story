"""Explicit opt-in composition; ordinary create_app never reads credentials."""

import os
from collections.abc import Mapping
from contextlib import asynccontextmanager
from pathlib import Path

from pydantic import model_validator

from storyforge.api.app import create_app
from storyforge.api.dependencies import Resources
from storyforge.config import AppSettings
from storyforge.validation.page_policy import PagePolicy
from storyforge.development.defaults import load_default_profiles
from storyforge.domain.base import Contract
from storyforge.llm.configuration import GeminiConfig, ModelCapabilities, OpenAIConfig
from storyforge.llm.gemini_provider import GeminiProvider, close_gemini_client, create_gemini_client
from storyforge.llm.openai_provider import OpenAIProvider, create_sdk_client
from storyforge.orchestration.budget import BudgetLimits, ModelPricing
from storyforge.orchestration.engine import StoryEngine


class StageConfiguration(Contract):
    capabilities: ModelCapabilities
    pricing: ModelPricing


class RuntimeConfiguration(Contract):
    page_policy: PagePolicy = PagePolicy()
    settings: AppSettings
    limits: BudgetLimits
    planner: StageConfiguration
    writer: StageConfiguration

    @model_validator(mode="after")
    def coherent_models(self) -> "RuntimeConfiguration":
        if self.settings.provider not in ("openai", "gemini"):
            raise ValueError("This runtime factory requires an implemented real provider")
        for stage in ("planner", "writer"):
            binding = getattr(self, stage)
            if (binding.capabilities.model != self.settings.model_for(stage)
                    or binding.pricing.model != binding.capabilities.model
                    or binding.pricing.provider != self.settings.provider):
                raise ValueError("Stage model and provider metadata must match")
        if (self.planner.capabilities.model == self.writer.capabilities.model
                and self.planner.capabilities != self.writer.capabilities):
            raise ValueError("One model cannot have conflicting capability declarations")
        return self


def load_configuration(environ: Mapping[str, str]) -> tuple[RuntimeConfiguration, OpenAIConfig | GeminiConfig]:
    """No dotenv discovery; explicit opt-in checked before any credential access."""
    if environ.get("STORYFORGE_ALLOW_PAID_CALLS") != "true":
        raise ValueError("Explicit paid-call opt-in is required")
    try:
        runtime = RuntimeConfiguration.model_validate_json(
            Path(environ["STORYFORGE_CONFIG"]).read_text(encoding="utf-8")
        )
        credential_type, variable = ((GeminiConfig, "GEMINI_API_KEY") if runtime.settings.provider == "gemini"
                                     else (OpenAIConfig, "OPENAI_API_KEY"))
        credentials = credential_type(api_key=environ[variable],
                                      timeout_seconds=runtime.settings.attempt_timeout_seconds)
    except Exception:
        raise ValueError("Invalid explicit runtime configuration or credentials") from None
    return runtime, credentials


def create_configured_app():
    """Optional live entrypoint. Construct/close a pool during lifespan; no probes."""
    app = create_app()

    @asynccontextmanager
    async def lifespan(application):
        runtime, credentials = load_configuration(os.environ)
        profiles = load_default_profiles()
        gemini = runtime.settings.provider == "gemini"
        client = create_gemini_client(credentials) if gemini else create_sdk_client(credentials)
        try:
            caps = (runtime.planner.capabilities, runtime.writer.capabilities)
            if caps[0] == caps[1]:
                caps = caps[:1]
            adapter = GeminiProvider if gemini else OpenAIProvider
            provider = adapter(client, credentials, caps)
            resources = Resources(
                profiles=profiles, settings=runtime.settings, limits=runtime.limits,
                pricing=runtime.planner.pricing, capabilities=runtime.planner.capabilities,
                writer_pricing=runtime.writer.pricing, writer_capabilities=runtime.writer.capabilities,
                provider=provider, page_policy=runtime.page_policy,
            )
            # Fail startup on invalid capacity/budget metadata without generating.
            StoryEngine(provider, profiles, settings=resources.settings, limits=resources.limits,
                        pricing=resources.pricing, capabilities=resources.capabilities,
                        writer_pricing=resources.writer_pricing, writer_capabilities=resources.writer_capabilities)
            application.state.resources = resources
            yield
        finally:
            application.state.resources = None
            if gemini:
                await close_gemini_client(client)
            else:
                await client.close()

    app.router.lifespan_context = lifespan
    return app
