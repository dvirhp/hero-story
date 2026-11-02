"""Conservative fake-only reservations, with no claims about real tokenizers."""

import json
from typing import Annotated, Literal

from pydantic import Field, model_validator

from storyforge.domain.base import Contract, Label, Money, PositiveInt
from storyforge.domain.generation import TokenUsage
from storyforge.llm.protocol import LLMRequest
from storyforge.llm.schema import structured_schema


class FakePricing(Contract):
    provider: Literal["fake"] = "fake"
    model: Literal["scripted-v1"] = "scripted-v1"
    version: Label = "fake-zero-v1"
    input_usd_per_million: Money = 0.0
    output_usd_per_million: Money = 0.0

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.input_usd_per_million
                + output_tokens * self.output_usd_per_million) / 1_000_000

    def usage_cost(self, usage: TokenUsage) -> float | None:
        if usage.source == "unknown":
            return None
        return self.cost(usage.input_tokens, usage.output_tokens)

    def reservation_cost(self, input_tokens: int, output_tokens: int) -> float:
        return self.cost(input_tokens, output_tokens)


class ModelPricing(Contract):
    provider: Literal["openai"] = "openai"
    model: Label
    version: Label
    reservation_input_usd_per_million: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    reservation_output_usd_per_million: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    input_usd_per_million: Money | None = None
    output_usd_per_million: Money | None = None
    cached_input_usd_per_million: Money | None = None

    @model_validator(mode="after")
    def conservative_rates(self) -> "ModelPricing":
        for rate in (self.input_usd_per_million, self.cached_input_usd_per_million):
            if rate is not None and rate > self.reservation_input_usd_per_million:
                raise ValueError("input reservation rate must cover configured input rates")
        if self.output_usd_per_million is not None and self.output_usd_per_million > self.reservation_output_usd_per_million:
            raise ValueError("output reservation rate must cover configured output rate")
        return self

    def reservation_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.reservation_input_usd_per_million
                + output_tokens * self.reservation_output_usd_per_million) / 1_000_000

    def usage_cost(self, usage: TokenUsage) -> float | None:
        if usage.source == "unknown" or self.input_usd_per_million is None or self.output_usd_per_million is None:
            return None
        cached = usage.cached_input_tokens or 0
        cached_rate = self.cached_input_usd_per_million
        if cached_rate is None:
            cached_rate = self.input_usd_per_million  # Explicit conservative estimate, not a double count.
        return ((usage.input_tokens - cached) * self.input_usd_per_million + cached * cached_rate
                + usage.output_tokens * self.output_usd_per_million) / 1_000_000


class BudgetLimits(Contract):
    version: Label = "budget-v1"
    max_total_tokens: PositiveInt = 33000
    max_cost_usd: Money = 0.0
    token_bound_version: Literal["fake-utf8-bytes-v1"] = "fake-utf8-bytes-v1"
    schema_overhead_tokens: Annotated[int, Field(ge=0)] = 256


def input_token_bound(request: LLMRequest, schema: type[Contract], overhead: int) -> int:
    """Synthetic upper bound: one token per UTF-8 byte plus explicit overhead.

    Includes instructions, input data and requested JSON schema. This is valid
    only for this fake execution policy, not a universal provider token count.
    """
    parts = (request.instructions, request.input_json,
             json.dumps(schema.model_json_schema(), ensure_ascii=False, sort_keys=True))
    return sum(len(part.encode("utf-8")) for part in parts) + overhead


def openai_input_bound(request: LLMRequest, schema: type[Contract], overhead: int) -> int:
    parts = (request.instructions, request.input_json,
             json.dumps(structured_schema(schema), ensure_ascii=False, sort_keys=True))
    return sum(len(part.encode("utf-8")) for part in parts) + overhead
