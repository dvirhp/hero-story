"""Conservative fake-only reservations, with no claims about real tokenizers."""

import json
from typing import Annotated, Literal

from pydantic import Field

from storyforge.domain.base import Contract, Label, Money, PositiveInt
from storyforge.domain.generation import TokenUsage
from storyforge.llm.protocol import LLMRequest


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
