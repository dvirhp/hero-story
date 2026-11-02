"""Typed quality, errors and usage metadata for future execution layers."""

import math
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, model_validator

from storyforge.domain.base import Contract, Label, Money, NonNegativeInt, PositiveInt, Seconds, Text
from storyforge.domain.story import Story

Stage = Literal["validation", "planner", "writer", "quality"]
ErrorCode = Literal[
    "INPUT_INVALID", "POLICY_REJECTED", "PROVIDER_OUTPUT_INVALID", "PROVIDER_UNAVAILABLE",
    "PROVIDER_REFUSED", "CONFIGURATION_ERROR", "DEADLINE_EXCEEDED", "CANCELLED",
    "BUDGET_EXCEEDED", "QUALITY_REJECTED",
]


class GenerationError(Contract):
    code: ErrorCode
    stage: Stage
    retryable: bool
    message: Label  # Caller supplies a safe message, never a raw provider diagnostic.


class TokenUsage(Contract):
    source: Literal["reported", "estimated", "unknown"]
    input_tokens: NonNegativeInt | None = None
    output_tokens: NonNegativeInt | None = None

    @model_validator(mode="after")
    def known_or_unknown(self) -> "TokenUsage":
        known = self.input_tokens is not None and self.output_tokens is not None
        if self.source == "unknown":
            if self.input_tokens is not None or self.output_tokens is not None:
                raise ValueError("unknown usage must not invent token counts")
        elif not known:
            raise ValueError("known usage requires both token counts")
        return self


class AttemptRecord(Contract):
    stage: Literal["planner", "writer"]
    attempt_number: PositiveInt
    provider: Label
    model: Label
    prompt_version: Label
    latency_seconds: Seconds
    usage: TokenUsage
    estimated_cost_usd: Money | None = None
    reserved_cost_usd: Money
    pricing_version: Label | None = None
    outcome: Literal["success", "failure"]
    error: GenerationError | None = None

    @model_validator(mode="after")
    def consistent_outcome(self) -> "AttemptRecord":
        if (self.outcome == "failure") != (self.error is not None):
            raise ValueError("only failed attempts require an error")
        if self.usage.source == "unknown" and self.estimated_cost_usd is not None:
            raise ValueError("unknown usage retains reservation, not a known cost")
        if self.estimated_cost_usd is not None and self.pricing_version is None:
            raise ValueError("estimated cost requires a pricing version")
        return self


class QualityIssue(Contract):
    code: Label
    severity: Literal["repairable", "terminal", "advisory"]
    page_number: PositiveInt | None = None
    guidance: Text


class QualityReport(Contract):
    passed: bool
    issues: tuple[QualityIssue, ...] = ()
    check_version: Label
    rubric_version: Label

    @model_validator(mode="after")
    def consistent_pass(self) -> "QualityReport":
        if self.passed == any(i.severity != "advisory" for i in self.issues):
            raise ValueError("pass flag must match blocking issues")
        return self


class UsageSummary(Contract):
    attempts: tuple[AttemptRecord, ...] = ()
    known_estimated_cost_usd: Money = 0.0
    upper_estimated_cost_usd: Money = 0.0
    has_unknown_usage: bool = False

    @model_validator(mode="after")
    def consistent_totals(self) -> "UsageSummary":
        if tuple(a.attempt_number for a in self.attempts) != tuple(range(1, len(self.attempts) + 1)):
            raise ValueError("attempt numbers must be contiguous from one")
        known = sum(a.estimated_cost_usd or 0.0 for a in self.attempts)
        upper = sum(a.reserved_cost_usd for a in self.attempts)
        unknown = any(a.usage.source == "unknown" for a in self.attempts)
        if (not math.isclose(self.known_estimated_cost_usd, known, abs_tol=1e-12)
                or not math.isclose(self.upper_estimated_cost_usd, upper, abs_tol=1e-12)
                or self.has_unknown_usage != unknown or known > upper):
            raise ValueError("usage summary must reflect attempt records and reservations")
        return self


class ResultBase(Contract):
    request_id: Label
    usage: UsageSummary
    total_latency_seconds: Seconds


class GenerationSuccess(ResultBase):
    status: Literal["success"] = "success"
    story: Story
    quality: QualityReport

    @model_validator(mode="after")
    def accepted_only(self) -> "GenerationSuccess":
        if not self.quality.passed:
            raise ValueError("success requires a passing quality report")
        return self


class GenerationFailure(ResultBase):
    status: Literal["failure"] = "failure"
    error: GenerationError
    quality: QualityReport | None = None


GenerationResult = Annotated[GenerationSuccess | GenerationFailure, Field(discriminator="status")]
generation_result_adapter = TypeAdapter(GenerationResult)
