"""Versioned developmental guidance and density; no book-length policy."""

from importlib.resources import files
from typing import Literal

from pydantic import model_validator

from storyforge.development.models import SoftGuidance, Strategy, WordRange
from storyforge.domain.base import Contract, Label, Language, NonNegativeInt, PositiveInt, Text

Density = Literal["light", "standard"]


class DensityRecommendation(Contract):
    density: Density
    words_per_page: WordRange


class LanguageDevelopment(Contract):
    language: Language
    reading_mode: Literal["adult_read_aloud", "shared_read_aloud"]
    strategy: Strategy
    densities: tuple[DensityRecommendation, ...]
    soft: SoftGuidance
    narrative_variety: Text

    @model_validator(mode="after")
    def complete_densities(self) -> "LanguageDevelopment":
        if sorted(item.density for item in self.densities) != ["light", "standard"]:
            raise ValueError("Exactly one recommendation per supported density is required")
        return self


class DevelopmentBand(Contract):
    band_id: Label
    min_months: NonNegativeInt
    max_months: PositiveInt | None
    provisional: Literal[True] = True
    languages: tuple[LanguageDevelopment, ...]

    @model_validator(mode="after")
    def valid_band(self) -> "DevelopmentBand":
        if self.max_months is not None and self.max_months <= self.min_months:
            raise ValueError("Invalid month interval")
        if sorted(item.language for item in self.languages) != ["en", "he"]:
            raise ValueError("Exactly one configuration per supported language is required")
        return self


class DevelopmentProfilesV2(Contract):
    version: Label
    bands: tuple[DevelopmentBand, ...]

    @model_validator(mode="after")
    def continuous(self) -> "DevelopmentProfilesV2":
        if not self.bands or self.bands[0].min_months != 0 or self.bands[-1].max_months is not None:
            raise ValueError("Coverage must start at zero and remain open-ended")
        if len({band.band_id for band in self.bands}) != len(self.bands):
            raise ValueError("Band IDs must be unique")
        if any(left.max_months != right.min_months for left, right in zip(self.bands, self.bands[1:])):
            raise ValueError("Bands must be ordered, contiguous and non-overlapping")
        return self


class DevelopmentSnapshotV2(Contract):
    band_id: Label
    version: Label
    min_months: NonNegativeInt
    max_months: PositiveInt | None
    requirements: LanguageDevelopment


def load_profiles_v2() -> DevelopmentProfilesV2:
    return DevelopmentProfilesV2.model_validate_json(
        files("storyforge.development").joinpath("profiles.v2.json").read_text(encoding="utf-8")
    )


def resolve_v2(config: DevelopmentProfilesV2, age_months: int, language: Language) -> DevelopmentSnapshotV2:
    # Public resolver validates strictly even when used outside normalization.
    from pydantic import TypeAdapter
    age = TypeAdapter(NonNegativeInt).validate_python(age_months, strict=True)
    selected_language = TypeAdapter(Language).validate_python(language, strict=True)
    band = next(band for band in config.bands if band.min_months <= age
                and (band.max_months is None or age < band.max_months))
    return DevelopmentSnapshotV2(band_id=band.band_id, version=config.version, min_months=band.min_months,
                                 max_months=band.max_months,
                                 requirements=next(item for item in band.languages if item.language == selected_language))
