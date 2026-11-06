"""Pure recovery classification and bounded, injectable retry scheduling."""

import math
from typing import Annotated

from pydantic import Field, model_validator

from storyforge.domain.base import Contract, Label
from storyforge.domain.generation import AttemptRecord


class RetrySettings(Contract):
    version: Label = "retry-v1"
    base_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 1.0
    maximum_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 8.0
    minimum_call_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 1.0

    @model_validator(mode="after")
    def ordered(self) -> "RetrySettings":
        if self.base_seconds > self.maximum_seconds:
            raise ValueError("Retry base must not exceed the maximum")
        return self

    def delay(self, failures: int, random_value: float, retry_after: float) -> float:
        if not math.isfinite(random_value) or not 0 <= random_value <= 1:
            raise ValueError("Retry randomness must be in [0, 1]")
        ceiling = min(self.maximum_seconds, self.base_seconds * 2 ** max(0, failures - 1))
        return max(retry_after, ceiling * (0.5 + 0.5 * random_value))


def is_transient(attempt: AttemptRecord) -> bool:
    return bool(attempt.error and attempt.error.retryable
                and attempt.error.code in ("PROVIDER_UNAVAILABLE", "DEADLINE_EXCEEDED"))


def needs_schema_recovery(attempt: AttemptRecord) -> bool:
    return bool(attempt.error and attempt.error.code == "PROVIDER_OUTPUT_INVALID"
                and attempt.provider_diagnostic.category != "output_truncated")


def consecutive_transient_failures(attempts: tuple[AttemptRecord, ...]) -> int:
    count = 0
    for attempt in reversed(attempts):
        if attempt.stage != attempts[-1].stage or not is_transient(attempt):
            break
        count += 1
    return count
