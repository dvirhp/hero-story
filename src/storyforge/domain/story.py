"""Request, brief, plan and story contracts; no quality-gate implementation."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from storyforge.development.models import DevelopmentalProfile, Strategy
from storyforge.domain.base import Contract, Label, Language, NonNegativeInt, PositiveInt, Text

Name = Annotated[str, StringConstraints(min_length=1, max_length=40, pattern=r"\S")]


class EnglishPronouns(Contract):
    language: Literal["en"]
    subject: Name
    object: Name
    possessive_determiner: Name
    possessive_pronoun: Name
    reflexive: Name
    verb_agreement: Literal["singular", "plural"]


class HebrewPronouns(Contract):
    language: Literal["he"]
    subject: Name
    object: Name
    possessive: Name
    grammatical_agreement: Literal["masculine_singular", "feminine_singular"]


NarrativePronouns = Annotated[EnglishPronouns | HebrewPronouns, Field(discriminator="language")]


class StoryRequest(Contract):
    language: Language
    display_name: Name
    age_months: NonNegativeInt
    theme: Label
    interests: Annotated[tuple[Name, ...], Field(max_length=5)] = ()
    narrative_pronouns: NarrativePronouns | None = None
    guidance: Annotated[str, StringConstraints(min_length=1, max_length=500, pattern=r"\S")] | None = None

    @model_validator(mode="after")
    def matching_pronouns(self) -> "StoryRequest":
        if self.narrative_pronouns and self.narrative_pronouns.language != self.language:
            raise ValueError("pronoun language must match story language")
        return self


class NormalizedBrief(Contract):
    request: StoryRequest
    profile: DevelopmentalProfile
    language_rubric_version: Label

    @model_validator(mode="after")
    def matching_profile(self) -> "NormalizedBrief":
        p = self.profile
        if (self.request.language != p.requirements.language
                or self.request.age_months < p.min_months
                or (p.max_months is not None and self.request.age_months >= p.max_months)):
            raise ValueError("profile must match request language and age")
        return self


class PageIntent(Contract):
    page_number: PositiveInt
    intent: Text


class PlotElements(Contract):
    goal: Text
    obstacle_or_choices: Text
    resolution: Text


class StoryPlan(Contract):
    language: Language
    title_concept: Label
    protagonist: Name
    strategy: Strategy
    pages: Annotated[tuple[PageIntent, ...], Field(min_length=1)]
    plot: PlotElements | None = None

    @model_validator(mode="after")
    def coherent_structure(self) -> "StoryPlan":
        if tuple(p.page_number for p in self.pages) != tuple(range(1, len(self.pages) + 1)):
            raise ValueError("page intents must be ordered and numbered from one")
        if self.strategy in ("simple_goal", "connected_scenes") and self.plot is None:
            raise ValueError("selected strategy requires plot elements")
        return self

    def validate_for(self, brief: NormalizedBrief) -> "StoryPlan":
        requirements = brief.profile.requirements
        if (self.language != brief.request.language or self.protagonist != brief.request.display_name
                or self.strategy != requirements.strategy
                or len(self.pages) != requirements.hard.page_count):
            raise ValueError("plan must match brief and profile constraints")
        return self


class StoryPage(Contract):
    page_id: Label
    page_number: PositiveInt
    text: Text


class Story(Contract):
    schema_version: Literal["1"] = "1"
    title: Label
    language: Language
    direction: Literal["ltr", "rtl"]
    profile_id: Label
    profile_version: Label
    pages: Annotated[tuple[StoryPage, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def ordered_pages(self) -> "Story":
        if self.direction != {"en": "ltr", "he": "rtl"}[self.language]:
            raise ValueError("direction must match language")
        if tuple(p.page_number for p in self.pages) != tuple(range(1, len(self.pages) + 1)):
            raise ValueError("pages must be ordered and numbered from one")
        if len({p.page_id for p in self.pages}) != len(self.pages):
            raise ValueError("page IDs must be unique")
        return self

    def validate_for(self, brief: NormalizedBrief) -> "Story":
        """Validate hard structural/length contracts, not developmental quality."""
        p = brief.profile
        hard = p.requirements.hard
        if (self.language != brief.request.language or self.profile_id != p.band_id
                or self.profile_version != p.version or len(self.pages) != hard.page_count):
            raise ValueError("story must match brief and profile metadata/page count")
        counts = tuple(len(page.text.split()) for page in self.pages)
        if any(not hard.words_per_page.minimum <= n <= hard.words_per_page.maximum for n in counts):
            raise ValueError("page word count outside configured hard range")
        if not hard.total_words.minimum <= sum(counts) <= hard.total_words.maximum:
            raise ValueError("total word count outside configured hard range")
        return self
