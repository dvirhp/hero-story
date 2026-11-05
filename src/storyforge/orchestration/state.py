"""Immutable runtime state; sensitive drafts stay internal to this process."""

from typing import Literal, TypedDict

from pydantic import Field, model_validator

from storyforge.domain.diagnostics import StopReason
from storyforge.domain.base import Contract, Label, Money, NonNegativeInt, Seconds
from storyforge.domain.generation import AttemptRecord, GenerationError, QualityReport, Stage, UsageSummary
from storyforge.domain.story import NormalizedBrief, Story, StoryPlan, StoryRequest
from storyforge.domain.story_v2 import NormalizedBriefV2, StoryPlanV2, StoryRequestV2, StoryV2


class RunState(Contract):
    request_id: Label
    raw_input: object = Field(repr=False)
    request: StoryRequestV2 | StoryRequest | None = Field(default=None, repr=False)
    brief: NormalizedBriefV2 | NormalizedBrief | None = Field(default=None, repr=False)
    plan: StoryPlanV2 | StoryPlan | None = Field(default=None, repr=False)
    draft: StoryV2 | Story | None = Field(default=None, repr=False)
    quality: QualityReport | None = None
    error: GenerationError | None = None
    stage: Stage = "validation"
    stop_reason: StopReason | None = None
    status: Literal["running", "success", "failure"] = "running"
    attempts: tuple[AttemptRecord, ...] = ()
    attempts_used: NonNegativeInt = 0
    token_reservations: tuple[int, ...] = ()
    rewrite_count: NonNegativeInt = 0
    started_at: Seconds
    deadline: Seconds
    simulated_seconds: Seconds = 0.0
    retry_after_seconds: Seconds = 0.0
    remaining_seconds: Seconds
    remaining_tokens: NonNegativeInt
    remaining_cost_usd: Money
    versions: tuple[tuple[str, str], ...]

    @model_validator(mode="after")
    def invariants(self) -> "RunState":
        if self.attempts_used != len(self.attempts) or len(self.token_reservations) != self.attempts_used:
            raise ValueError("attempt reservations and ledger must agree")
        if tuple(a.attempt_number for a in self.attempts) != tuple(range(1, self.attempts_used + 1)):
            raise ValueError("attempt records must be contiguous from one")
        if self.plan is not None and self.brief is None:
            raise ValueError("a plan requires a normalized brief")
        if self.draft is not None and self.plan is None:
            raise ValueError("a draft requires a validated plan")
        if self.attempts_used > 3 or self.rewrite_count > 1 or any(n < 0 for n in self.token_reservations):
            raise ValueError("execution bounds exceeded")
        if self.status == "success" and (self.draft is None or self.quality is None
                                         or not self.quality.passed or self.error is not None):
            raise ValueError("success requires an approved draft and no error")
        if self.status == "failure" and self.error is None:
            raise ValueError("failure requires a typed error")
        return self

    def updated(self, **changes: object) -> "RunState":
        return RunState.model_validate({**self.__dict__, **changes})

    def usage(self) -> UsageSummary:
        return UsageSummary(
            attempts=self.attempts,
            known_estimated_cost_usd=sum(a.estimated_cost_usd or 0.0 for a in self.attempts),
            upper_estimated_cost_usd=sum(a.reserved_cost_usd for a in self.attempts),
            has_unknown_usage=any(a.usage.source == "unknown" for a in self.attempts),
        )


class GraphState(TypedDict):
    run: RunState
