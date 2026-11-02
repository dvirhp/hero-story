"""Explicit, validated offline settings; no environment or credential reads."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from storyforge.domain.base import Contract, PositiveInt


class AppSettings(Contract):
    provider: Literal["fake"] = "fake"
    model: Literal["scripted-v1"] = "scripted-v1"
    max_attempts: Annotated[int, Field(ge=1, le=3)] = 3
    max_quality_rewrites: Annotated[int, Field(ge=0, le=1)] = 1
    planner_output_tokens: PositiveInt = 1200
    writer_output_tokens: PositiveInt = 3000
    max_input_tokens: PositiveInt = 8000
    attempt_timeout_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 30.0
    request_timeout_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 90.0

    @model_validator(mode="after")
    def valid_limits(self) -> "AppSettings":
        if self.max_attempts < 2:
            raise ValueError("planner and writer require at least two attempt slots")
        if self.attempt_timeout_seconds > self.request_timeout_seconds:
            raise ValueError("attempt timeout must not exceed request timeout")
        if self.max_quality_rewrites > self.max_attempts - 2:
            raise ValueError("rewrite allowance requires an extra attempt slot")
        return self
