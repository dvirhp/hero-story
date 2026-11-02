"""Strict v2 book contracts: user length, developmental guidance, typed coverage."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from storyforge.development.models import WordRange
from storyforge.development.v2 import Density, DevelopmentSnapshotV2
from storyforge.domain.base import Contract, Label, PositiveInt
from storyforge.domain.story import Name, Story, StoryPage, StoryPlan, StoryRequest, PageIntent

ShortText = Annotated[str, StringConstraints(min_length=1, max_length=400, pattern=r"\S")]


class EducationalTarget(Contract):
    target_id: Label
    label: Name
    kind: Literal["concept", "letter"] = "concept"
    base_form: Name | None = None
    example_word: Name | None = None

    @model_validator(mode="after")
    def consistent_form(self) -> "EducationalTarget":
        if self.base_form is not None:
            if self.kind != "letter" or not self.example_word or not self.example_word.endswith(self.label):
                raise ValueError("A final-form target requires a letter and an example ending in that form")
            if self.label == self.base_form:
                raise ValueError("Final form must differ from base form")
        return self


class SentenceUnits(Contract):
    minimum: PositiveInt
    maximum: PositiveInt

    @model_validator(mode="after")
    def ordered(self) -> "SentenceUnits":
        if self.minimum > self.maximum:
            raise ValueError("Invalid sentence-unit range")
        return self


class OrderedTargets(Contract):
    kind: Literal["ordered_targets"] = "ordered_targets"
    targets: Annotated[tuple[EducationalTarget, ...], Field(min_length=1)]
    sentence_units_per_page: SentenceUnits | None = None

    @model_validator(mode="after")
    def unique_ids(self) -> "OrderedTargets":
        if len({target.target_id for target in self.targets}) != len(self.targets):
            raise ValueError("Target IDs must be unique")
        return self


class StoryRequestV2(StoryRequest):
    schema_version: Literal["2"] = "2"
    page_count: PositiveInt  # Operational min/max belong to configurable PagePolicy.
    story_type: Literal["general", "bedtime", "adventure", "educational", "alphabet"] = "general"
    text_density: Density = "standard"
    structure: OrderedTargets | None = None
    requested_title: Label | None = None

    @model_validator(mode="after")
    def coherent_structure(self) -> "StoryRequestV2":
        if self.structure and len(self.structure.targets) != self.page_count:
            raise ValueError("One ordered target is required per requested page")
        if self.story_type == "alphabet":
            if self.structure is None or any(target.kind != "letter" for target in self.structure.targets):
                raise ValueError("Alphabet books require explicit ordered letter targets")
            labels = [target.label for target in self.structure.targets]
            if len(set(labels)) != len(labels):
                raise ValueError("Alphabet target labels must be unique")
            for index, target in enumerate(self.structure.targets):
                if target.base_form is not None and target.base_form not in labels[:index]:
                    raise ValueError("A final form must reference an earlier base-letter target")
        return self


class BookConstraints(Contract):
    page_count: PositiveInt
    words_per_page: WordRange
    total_words: WordRange
    target_ids: tuple[Label, ...] = ()
    sentence_units_per_page: SentenceUnits | None = None
    policy_version: Label

    @model_validator(mode="after")
    def derived_lengths(self) -> "BookConstraints":
        if (self.total_words.minimum != self.page_count * self.words_per_page.minimum
                or self.total_words.maximum != self.page_count * self.words_per_page.maximum):
            raise ValueError("Total length must be derived from requested pages and density")
        if self.target_ids and len(self.target_ids) != self.page_count:
            raise ValueError("Target assignments must match page count")
        return self


class ExecutionAllocation(Contract):
    planner_output_tokens: PositiveInt
    writer_output_tokens: PositiveInt
    estimate_version: Label


class NormalizedBriefV2(Contract):
    request: StoryRequestV2
    profile: DevelopmentSnapshotV2
    constraints: BookConstraints
    execution: ExecutionAllocation
    language_rubric_version: Label

    @model_validator(mode="after")
    def consistent_snapshot(self) -> "NormalizedBriefV2":
        request, profile, constraints = self.request, self.profile, self.constraints
        if (request.language != profile.requirements.language or request.age_months < profile.min_months
                or (profile.max_months is not None and request.age_months >= profile.max_months)
                or request.page_count != constraints.page_count):
            raise ValueError("Resolved book must match request and developmental profile")
        expected_ids = tuple(target.target_id for target in request.structure.targets) if request.structure else ()
        if constraints.target_ids != expected_ids:
            raise ValueError("Target snapshot must match requested ordered targets")
        expected_units = request.structure.sentence_units_per_page if request.structure else None
        if constraints.sentence_units_per_page != expected_units:
            raise ValueError("Sentence-unit snapshot must match request")
        return self


class PageIntentV2(PageIntent):
    intent: ShortText
    progression: ShortText
    target_id: Label | None = None


class StoryPlanV2(StoryPlan):
    schema_version: Literal["2"] = "2"
    page_count: PositiveInt
    pages: Annotated[tuple[PageIntentV2, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def count_matches_pages(self) -> "StoryPlanV2":
        if self.page_count != len(self.pages):
            raise ValueError("Declared plan count must match actual pages")
        return self

    def validate_for(self, brief: NormalizedBriefV2) -> "StoryPlanV2":
        expected = brief.constraints.target_ids or (None,) * brief.request.page_count
        if (self.page_count != brief.request.page_count or len(self.pages) != self.page_count
                or self.language != brief.request.language or self.protagonist != brief.request.display_name
                or self.strategy != brief.profile.requirements.strategy
                or tuple(page.target_id for page in self.pages) != expected):
            raise ValueError("Plan must match requested length, targets and developmental strategy")
        return self


class StoryPageV2(StoryPage):
    target_id: Label | None = None
    sentence_units: Annotated[tuple[ShortText, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def single_text_representation(self) -> "StoryPageV2":
        if self.text != " ".join(self.sentence_units):
            raise ValueError("Page text must exactly equal joined sentence units")
        return self


class StoryV2(Story):
    schema_version: Literal["2"] = "2"
    page_count: PositiveInt
    pages: Annotated[tuple[StoryPageV2, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def count_matches_pages(self) -> "StoryV2":
        if self.page_count != len(self.pages):
            raise ValueError("Declared story count must match actual pages")
        return self

    def validate_for(self, brief: NormalizedBriefV2) -> "StoryV2":
        hard = brief.constraints
        if (self.page_count != brief.request.page_count or len(self.pages) != hard.page_count
                or self.language != brief.request.language or self.profile_id != brief.profile.band_id
                or self.profile_version != brief.profile.version):
            raise ValueError("Story must match requested length and resolved metadata")
        counts = [len(page.text.split()) for page in self.pages]
        if any(not hard.words_per_page.minimum <= count <= hard.words_per_page.maximum for count in counts):
            raise ValueError("Page word count outside configured density")
        if not hard.total_words.minimum <= sum(counts) <= hard.total_words.maximum:
            raise ValueError("Total word count outside derived range")
        if tuple(page.target_id for page in self.pages) != (hard.target_ids or (None,) * hard.page_count):
            raise ValueError("Story target order must match request")
        if brief.request.requested_title and self.title != brief.request.requested_title:
            raise ValueError("Story title must match the requested title")
        if hard.sentence_units_per_page and any(
            not hard.sentence_units_per_page.minimum <= len(page.sentence_units) <= hard.sentence_units_per_page.maximum
            for page in self.pages
        ):
            raise ValueError("Sentence-unit count must match request")
        return self
