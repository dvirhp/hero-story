"""Request-local engine injection; shared resources contain no child content."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from storyforge.config import AppSettings
from storyforge.development.models import DevelopmentConfig
from storyforge.development.v2 import DevelopmentProfilesV2
from storyforge.validation.page_policy import PagePolicy
from storyforge.llm.fixtures import LocalFixtureProvider
from storyforge.llm.protocol import LLMProvider
from storyforge.llm.configuration import ModelCapabilities
from storyforge.orchestration.budget import BudgetLimits, FakePricing, ModelPricing
from storyforge.orchestration.engine import StoryEngine
from storyforge.quality.rules import DEFAULT_RULES, QualityRules


@dataclass(frozen=True)
class Resources:
    profiles: DevelopmentConfig
    settings: AppSettings = AppSettings()
    limits: BudgetLimits = BudgetLimits()
    pricing: FakePricing | ModelPricing = FakePricing()
    capabilities: ModelCapabilities | None = None
    writer_pricing: ModelPricing | None = None
    writer_capabilities: ModelCapabilities | None = None
    provider: LLMProvider | None = None
    rules: QualityRules = DEFAULT_RULES
    page_policy: PagePolicy = PagePolicy()
    profiles_v2: DevelopmentProfilesV2 | None = None
    clock: Callable[[], float] = time.monotonic


async def get_resources(request: Request) -> Resources:
    resources = getattr(request.app.state, "resources", None)
    if resources is None:
        raise RuntimeError("Application lifespan has not started")
    return resources


async def get_provider(resources: Annotated[Resources, Depends(get_resources)]) -> LLMProvider:
    if resources.provider is None and resources.settings.provider != "fake":
        raise ValueError("Real mode requires an explicitly injected provider")
    return resources.provider if resources.provider is not None else LocalFixtureProvider(rules=resources.rules)


async def get_engine(
    resources: Annotated[Resources, Depends(get_resources)],
    provider: Annotated[LLMProvider, Depends(get_provider)],
) -> StoryEngine:
    return StoryEngine(provider, resources.profiles, settings=resources.settings, limits=resources.limits,
                       pricing=resources.pricing, rules=resources.rules, clock=resources.clock,
                       capabilities=resources.capabilities, writer_pricing=resources.writer_pricing,
                       writer_capabilities=resources.writer_capabilities)


async def get_engine_v2(
    resources: Annotated[Resources, Depends(get_resources)],
    provider: Annotated[LLMProvider, Depends(get_provider)],
) -> StoryEngine:
    return StoryEngine(provider, resources.profiles, settings=resources.settings, limits=resources.limits,
                       pricing=resources.pricing, rules=resources.rules, clock=resources.clock,
                       capabilities=resources.capabilities, writer_pricing=resources.writer_pricing,
                       writer_capabilities=resources.writer_capabilities, contract_version="2",
                       profiles_v2=resources.profiles_v2, page_policy=resources.page_policy)
