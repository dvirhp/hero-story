"""Request-local engine injection; shared resources contain no child content."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from storyforge.config import AppSettings
from storyforge.development.models import DevelopmentConfig
from storyforge.llm.fixtures import LocalFixtureProvider
from storyforge.llm.protocol import LLMProvider
from storyforge.orchestration.budget import BudgetLimits, FakePricing
from storyforge.orchestration.engine import StoryEngine
from storyforge.quality.rules import DEFAULT_RULES, QualityRules


@dataclass(frozen=True)
class Resources:
    profiles: DevelopmentConfig
    settings: AppSettings = AppSettings()
    limits: BudgetLimits = BudgetLimits()
    pricing: FakePricing = FakePricing()
    rules: QualityRules = DEFAULT_RULES
    clock: Callable[[], float] = time.monotonic


async def get_resources(request: Request) -> Resources:
    resources = getattr(request.app.state, "resources", None)
    if resources is None:
        raise RuntimeError("Application lifespan has not started")
    return resources


async def get_provider(resources: Annotated[Resources, Depends(get_resources)]) -> LLMProvider:
    return LocalFixtureProvider(rules=resources.rules)


async def get_engine(
    resources: Annotated[Resources, Depends(get_resources)],
    provider: Annotated[LLMProvider, Depends(get_provider)],
) -> StoryEngine:
    return StoryEngine(provider, resources.profiles, settings=resources.settings, limits=resources.limits,
                       pricing=resources.pricing, rules=resources.rules, clock=resources.clock)
