"""Request, brief, plan and story contracts; no quality-gate implementation."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from storyforge.development.models import DevelopmentalProfile, Strategy
from storyforge.domain.base import Contract, Label, Language, NonNegativeInt, PositiveInt, Text
from storyforge.domain.output_validation import OutputContractError

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
        for index, page in enumerate(self.pages):
            if page.page_number != index + 1:
                raise OutputContractError("page_order", path=("pages", index, "page_number"))
        if self.strategy in ("simple_goal", "connected_scenes") and self.plot is None:
            raise OutputContractError("plot_missing", path=("plot",))
        return self

    def validate_for(self, brief: NormalizedBrief) -> "StoryPlan":
        requirements = brief.profile.requirements
        if self.language != brief.request.language:
            raise OutputContractError("language_mismatch", path=("language",))
        if self.protagonist != brief.request.display_name:
            raise OutputContractError("plan_context_mismatch", path=("protagonist",))
        if self.strategy != requirements.strategy:
            raise OutputContractError("plan_context_mismatch", path=("strategy",))
        if len(self.pages) != requirements.hard.page_count:
            raise OutputContractError("page_count_mismatch", path=("pages",), observed_count=len(self.pages),
                minimum_count=requirements.hard.page_count, maximum_count=requirements.hard.page_count)
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
            raise OutputContractError("direction_mismatch", path=("direction",))
        seen = set()
        for index, page in enumerate(self.pages):
            if page.page_number != index + 1:
                raise OutputContractError("page_order", path=("pages", index, "page_number"))
            if page.page_id in seen:
                raise OutputContractError("duplicate_page_id", path=("pages", index, "page_id"))
            seen.add(page.page_id)
        return self

    def validate_for(self, brief: NormalizedBrief) -> "Story":
        """Validate hard structural/length contracts, not developmental quality."""
        p = brief.profile
        hard = p.requirements.hard
        if self.language != brief.request.language:
            raise OutputContractError("language_mismatch", path=("language",))
        if self.profile_id != p.band_id:
            raise OutputContractError("profile_mismatch", path=("profile_id",))
        if self.profile_version != p.version:
            raise OutputContractError("profile_mismatch", path=("profile_version",))
        if len(self.pages) != hard.page_count:
            raise OutputContractError("page_count_mismatch", path=("pages",), observed_count=len(self.pages),
                minimum_count=hard.page_count, maximum_count=hard.page_count)
        counts = tuple(len(page.text.split()) for page in self.pages)
        for index, count in enumerate(counts):
            if not hard.words_per_page.minimum <= count <= hard.words_per_page.maximum:
                raise OutputContractError("page_word_count", path=("pages", index), observed_count=count,
                    minimum_count=hard.words_per_page.minimum, maximum_count=hard.words_per_page.maximum)
        if not hard.total_words.minimum <= sum(counts) <= hard.total_words.maximum:
            raise OutputContractError("total_word_count", observed_count=sum(counts),
                minimum_count=hard.total_words.minimum, maximum_count=hard.total_words.maximum)
        return self
