"""Explicit, validated execution settings; no environment or credential reads."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from storyforge.domain.base import Contract, Label, PositiveInt
from storyforge.orchestration.recovery import RetrySettings


class AppSettings(Contract):
    provider: Literal["fake", "openai", "gemini"] = "fake"
    model: Label = "scripted-v1"
    planner_model: Label | None = None
    writer_model: Label | None = None

    def model_for(self, stage: Literal["planner", "writer"]) -> str:
        return (self.planner_model if stage == "planner" else self.writer_model) or self.model

    max_attempts: Annotated[int, Field(ge=1, le=3)] = 3
    max_quality_rewrites: Annotated[int, Field(ge=0, le=1)] = 1
    planner_output_tokens: PositiveInt = 1200
    writer_output_tokens: PositiveInt = 3000
    max_input_tokens: PositiveInt = 8000
    attempt_timeout_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 30.0
    request_timeout_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 90.0
    retry: RetrySettings = RetrySettings()

    @model_validator(mode="after")
    def valid_limits(self) -> "AppSettings":
        if self.provider == "fake" and any(self.model_for(stage) != "scripted-v1" for stage in ("planner", "writer")):
            raise ValueError("fake mode requires the scripted model")
        if self.provider != "fake" and any(self.model_for(stage) == "scripted-v1" for stage in ("planner", "writer")):
            raise ValueError("Real provider mode requires an explicit model ID")
        if self.max_attempts < 2:
            raise ValueError("planner and writer require at least two attempt slots")
        if self.attempt_timeout_seconds > self.request_timeout_seconds:
            raise ValueError("attempt timeout must not exceed request timeout")
        if self.max_quality_rewrites > self.max_attempts - 2:
            raise ValueError("rewrite allowance requires an extra attempt slot")
        return self
