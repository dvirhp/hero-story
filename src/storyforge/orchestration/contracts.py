"""Select versioned contracts at composition time; graph routing stays shared."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from storyforge.config import AppSettings
from storyforge.development.models import DevelopmentConfig
from storyforge.development.v2 import DevelopmentProfilesV2, load_profiles_v2
from storyforge.domain.base import Contract
from storyforge.domain.generation import GenerationSuccess
from storyforge.domain.generation_v2 import GenerationSuccessV2
from storyforge.domain.story import Story, StoryPlan, StoryRequest
from storyforge.domain.story_v2 import StoryPlanV2, StoryRequestV2, StoryV2
from storyforge.prompts.builders import PLANNER_VERSION, WRITER_VERSION, build_request
from storyforge.prompts.v2 import PLANNER_VERSION_V2, WRITER_VERSION_V2, build_request_v2
from storyforge.quality.rules import QualityRules
from storyforge.validation.normalization import normalize_request
from storyforge.validation.normalization_v2 import normalize_v2
from storyforge.validation.page_policy import PagePolicy


@dataclass(frozen=True)
class ExecutionContracts:
    request_schema: type[Contract]
    plan_schema: type[Contract]
    story_schema: type[Contract]
    success_schema: type[Contract]
    normalize: Callable[[Any], Contract]
    build_prompt: Callable[..., Any]
    profile_version: str
    planner_prompt_version: str
    writer_prompt_version: str


def execution_contracts(version: Literal["1", "2"], profiles: DevelopmentConfig, settings: AppSettings,
                        rules: QualityRules, page_policy: PagePolicy,
                        profiles_v2: DevelopmentProfilesV2 | None = None) -> ExecutionContracts:
    if version == "1":
        return ExecutionContracts(StoryRequest, StoryPlan, Story, GenerationSuccess,
                                  lambda request: normalize_request(request, profiles, rules), build_request,
                                  profiles.version, PLANNER_VERSION, WRITER_VERSION)
    if version != "2":
        raise ValueError("Unsupported execution contract version")
    current = profiles_v2 if profiles_v2 is not None else load_profiles_v2()
    return ExecutionContracts(StoryRequestV2, StoryPlanV2, StoryV2, GenerationSuccessV2,
                              lambda request: normalize_v2(request, current, settings=settings,
                                                           page_policy=page_policy, rules=rules), build_request_v2,
                              current.version, PLANNER_VERSION_V2, WRITER_VERSION_V2)
