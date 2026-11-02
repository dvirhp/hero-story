"""Async structured-output protocol, with explicit limits and usage."""

from typing import Annotated, Generic, Literal, Protocol, TypeVar

import json

from pydantic import BaseModel, Field, field_validator

from storyforge.domain.base import Contract, Label, PositiveInt, Seconds, Text
from storyforge.domain.generation import GenerationError, QualityReport, TokenUsage

OutputT = TypeVar("OutputT", bound=BaseModel)


class LLMRequest(Contract):
    stage: Literal["planner", "writer"]
    model: Label
    prompt_version: Label
    instructions: Text
    input_json: Annotated[str, Field(min_length=2, max_length=100000)]
    max_output_tokens: PositiveInt
    remaining_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)]

    @field_validator("input_json")
    @classmethod
    def json_object(cls, value: str) -> str:
        def reject_constant(value: str) -> None:
            raise ValueError("non-finite JSON numbers are unsupported")

        if not isinstance(json.loads(value, parse_constant=reject_constant), dict):
            raise ValueError("provider input must be a serialized JSON object")
        return value


class ProviderSuccess(Contract, Generic[OutputT]):
    status: Literal["success"] = "success"
    provider: Label
    model: Label
    payload: OutputT
    usage: TokenUsage
    latency_seconds: Seconds


class ProviderFailure(Contract):
    status: Literal["failure"] = "failure"
    provider: Label
    model: Label
    error: GenerationError
    usage: TokenUsage
    latency_seconds: Seconds
    quality: QualityReport | None = None
    retry_after_seconds: Seconds | None = None


class LLMProvider(Protocol):
    async def generate(
        self, request: LLMRequest, output_schema: type[OutputT],
    ) -> ProviderSuccess[OutputT] | ProviderFailure:
        """One attempt only; callers own budgets and retries. Never log content."""
        ...
