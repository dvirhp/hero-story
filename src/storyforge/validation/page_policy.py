"""Configurable v2 admission and token sizing, independent of provider SDKs."""

import math
from typing import Annotated

from pydantic import Field, model_validator

from storyforge.config import AppSettings
from storyforge.domain.base import Contract, Label, Language, PositiveInt
from storyforge.domain.story_v2 import ExecutionAllocation


class LanguageTokenEstimate(Contract):
    language: Language
    tokens_per_word: Annotated[float, Field(gt=0, allow_inf_nan=False)]


class PagePolicy(Contract):
    version: Label = "page-policy-v2-2"
    minimum_pages: PositiveInt = 1
    maximum_pages: PositiveInt = 32
    planner_base_tokens: PositiveInt = 256
    planner_tokens_per_page: PositiveInt = 112
    planner_thinking_allowance_tokens: Annotated[int, Field(ge=0)] = 256
    writer_base_tokens: PositiveInt = 256
    writer_json_tokens_per_page: PositiveInt = 64
    thinking_allowance_tokens: Annotated[int, Field(ge=0)] = 1024
    output_headroom_ratio: Annotated[float, Field(ge=1, allow_inf_nan=False)] = 1.25
    language_estimates: tuple[LanguageTokenEstimate, ...] = (
        LanguageTokenEstimate(language="en", tokens_per_word=2.0),
        LanguageTokenEstimate(language="he", tokens_per_word=4.0),
    )

    @model_validator(mode="after")
    def valid_policy(self) -> "PagePolicy":
        if self.minimum_pages > self.maximum_pages:
            raise ValueError("Invalid operational page interval")
        if sorted(item.language for item in self.language_estimates) != ["en", "he"]:
            raise ValueError("Exactly one sizing estimate per supported language is required")
        return self

    def allocate(self, pages: int, max_words_per_page: int, language: Language,
                 settings: AppSettings) -> ExecutionAllocation:
        if not self.minimum_pages <= pages <= self.maximum_pages:
            raise ValueError("Requested page count outside configured service range")
        ratio = next(item.tokens_per_word for item in self.language_estimates if item.language == language)
        planner = (self.planner_base_tokens + pages * self.planner_tokens_per_page
                   + self.planner_thinking_allowance_tokens)
        # Visible JSON (including page metadata) gets headroom independently of
        # thinking. These are versioned offline estimates, not tokenizer claims.
        visible = self.writer_base_tokens + pages * (
            self.writer_json_tokens_per_page + math.ceil(max_words_per_page * ratio))
        writer = math.ceil(visible * self.output_headroom_ratio) + self.thinking_allowance_tokens
        # Never clamp and pretend the requested book still has sufficient space.
        if planner > settings.planner_output_tokens or writer > settings.writer_output_tokens:
            raise OverflowError("Book estimate exceeds configured stage output ceilings")
        return ExecutionAllocation(planner_output_tokens=planner, writer_output_tokens=writer,
                                   estimate_version=self.version)
