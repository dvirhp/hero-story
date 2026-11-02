"""Declarative profile contracts; guidance represents product hypotheses."""

from typing import Literal

from pydantic import model_validator

from storyforge.domain.base import Contract, Label, Language, NonNegativeInt, PositiveInt, Text

Strategy = Literal["sensory", "noticing", "routine", "simple_goal", "connected_scenes"]


class WordRange(Contract):
    minimum: PositiveInt
    maximum: PositiveInt

    @model_validator(mode="after")
    def ordered(self) -> "WordRange":
        if self.minimum > self.maximum:
            raise ValueError("minimum must not exceed maximum")
        return self


class HardConstraints(Contract):
    page_count: PositiveInt
    words_per_page: WordRange
    total_words: WordRange

    @model_validator(mode="after")
    def feasible(self) -> "HardConstraints":
        if (self.total_words.minimum < self.page_count * self.words_per_page.minimum
                or self.total_words.maximum > self.page_count * self.words_per_page.maximum):
            raise ValueError("total word range must fit page count and per-page range")
        return self


class SoftGuidance(Contract):
    vocabulary: Text
    sentence_words: WordRange
    repetition: Text
    developmental_guidance: Text


class LanguageProfile(Contract):
    language: Language
    reading_mode: Literal["adult_read_aloud", "shared_read_aloud"]
    strategy: Strategy
    hard: HardConstraints
    soft: SoftGuidance


class AgeBand(Contract):
    band_id: Label
    min_months: NonNegativeInt
    max_months: PositiveInt | None
    provisional: bool = True
    languages: tuple[LanguageProfile, ...]

    @model_validator(mode="after")
    def valid_band(self) -> "AgeBand":
        if self.max_months is not None and self.max_months <= self.min_months:
            raise ValueError("empty age band")
        if sorted(p.language for p in self.languages) != ["en", "he"]:
            raise ValueError("exactly one English and one Hebrew profile required")
        return self


class DevelopmentConfig(Contract):
    version: Label
    bands: tuple[AgeBand, ...]

    @model_validator(mode="after")
    def continuous(self) -> "DevelopmentConfig":
        if not self.bands or self.bands[0].min_months != 0:
            raise ValueError("coverage must start at zero")
        if len({b.band_id for b in self.bands}) != len(self.bands):
            raise ValueError("band IDs must be unique")
        for left, right in zip(self.bands, self.bands[1:]):
            if left.max_months != right.min_months:
                raise ValueError("bands must be ordered, contiguous and non-overlapping")
        if self.bands[-1].max_months is not None:
            raise ValueError("final band must be open-ended")
        return self


class DevelopmentalProfile(Contract):
    band_id: Label
    version: Label
    min_months: NonNegativeInt
    max_months: PositiveInt | None
    provisional: bool
    requirements: LanguageProfile

    @model_validator(mode="after")
    def valid_bounds(self) -> "DevelopmentalProfile":
        if self.max_months is not None and self.max_months <= self.min_months:
            raise ValueError("empty age band")
        return self
