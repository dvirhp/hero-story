"""Scripted adapter: validates outputs, never networks, retries or sleeps."""

from collections import deque
from typing import Annotated

from pydantic import Field, ValidationError, model_validator

from storyforge.domain.base import Contract, Seconds
from storyforge.domain.generation import GenerationError, TokenUsage
from storyforge.llm.protocol import LLMRequest, OutputT, ProviderFailure, ProviderSuccess


class FakeStep(Contract):
    """Exactly one of raw response JSON or a normalized error is scripted."""

    response_json: Annotated[str, Field(max_length=100000)] | None = None
    error: GenerationError | None = None
    usage: TokenUsage = TokenUsage(source="unknown")
    latency_seconds: Seconds = 0.0

    @model_validator(mode="after")
    def one_outcome(self) -> "FakeStep":
        if (self.response_json is None) == (self.error is None):
            raise ValueError("script exactly one response or error")
        return self


class FakeProvider:
    def __init__(self, steps: tuple[FakeStep, ...]) -> None:
        self._steps = deque(steps)
        self._calls: list[LLMRequest] = []

    @property
    def calls(self) -> tuple[LLMRequest, ...]:
        """In-memory assertions only; contains instructions and must not be logged."""
        return tuple(self._calls)

    async def generate(
        self, request: LLMRequest, output_schema: type[OutputT],
    ) -> ProviderSuccess[OutputT] | ProviderFailure:
        if not self._steps:
            raise RuntimeError("fake provider script exhausted")
        step = self._steps.popleft()
        self._calls.append(request)
        common = dict(provider="fake", model=request.model, usage=step.usage,
                      latency_seconds=step.latency_seconds)
        if step.latency_seconds > request.remaining_seconds:
            return ProviderFailure(**{**common, "latency_seconds": request.remaining_seconds},
                                   error=GenerationError(code="DEADLINE_EXCEEDED", stage=request.stage,
                                                         retryable=True, message="Attempt timed out"))
        if step.error is not None:
            if step.error.stage != request.stage:
                raise ValueError("scripted error stage must match requested stage")
            return ProviderFailure(**common, error=step.error)
        try:
            payload = output_schema.model_validate_json(step.response_json, strict=True)
        except ValidationError:
            return ProviderFailure(**common, error=GenerationError(
                code="PROVIDER_OUTPUT_INVALID", stage=request.stage, retryable=True,
                message="Provider output did not match schema"))
        return ProviderSuccess[output_schema](**common, payload=payload)
