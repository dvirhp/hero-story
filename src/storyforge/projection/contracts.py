"""Strict initial AI variants of Agent 3's documented canonical wire shapes.

These are not the editable, multimode Book aggregate or HTTP DTO registry.
"""

from datetime import datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, StringConstraints, model_validator

from storyforge.domain.base import Contract, Label, Language, PositiveInt
from storyforge.quality.text import forbidden_controls

Unit = Annotated[str, StringConstraints(min_length=1, max_length=400, pattern=r"\S")]


class ProjectionContract(Contract):
    model_config = ConfigDict(revalidate_instances="always")

    @model_validator(mode="after")
    def safe_unicode(self) -> "ProjectionContract":
        from storyforge.quality.text import string_values

        if any(forbidden_controls(value) for value in string_values(self.model_dump())):
            raise ValueError("Unsupported Unicode controls")
        return self


class TextLayout(ProjectionContract):
    preset: Literal["text-only-v1"] = "text-only-v1"


class AITextBlock(ProjectionContract):
    kind: Literal["text"] = "text"
    block_id: Literal["body"] = "body"
    language: Language
    direction: Literal["rtl", "ltr"]
    style: Literal["body"] = "body"
    sentence_units: Annotated[tuple[Unit, ...], Field(min_length=1, max_length=128)]

    @model_validator(mode="after")
    def matching_direction(self) -> "AITextBlock":
        if self.direction != {"he": "rtl", "en": "ltr"}[self.language]:
            raise ValueError("Direction must match language")
        return self


class AITextPageDocument(ProjectionContract):
    schema_version: Literal["1"] = "1"
    layout: TextLayout = TextLayout()
    blocks: Annotated[tuple[AITextBlock, ...], Field(min_length=1, max_length=1)]


class AITextBookPage(ProjectionContract):
    page_id: UUID
    position: PositiveInt
    document: AITextPageDocument
    asset_bindings: tuple[()] = ()
    source_page_key: Label
    source_target_id: Label | None

    @model_validator(mode="after")
    def independent_identity(self) -> "AITextBookPage":
        if str(self.page_id) == self.source_page_key:
            raise ValueError("Canonical page identity must be separate")
        return self


class AIOrigin(ProjectionContract):
    generation_id: UUID
    template_version_id: None = None
    page_variant_id: None = None
    source_display: None = None


class AITextBookProjection(ProjectionContract):
    schema_version: Literal["1"] = "1"
    book_id: UUID
    creation_mode: Literal["AI_GENERATED"] = "AI_GENERATED"
    state: Literal["draft"] = "draft"
    revision: Annotated[int, Field(ge=1, le=1)] = 1
    title: Label
    language: Language
    direction: Literal["rtl", "ltr"]
    page_count: PositiveInt
    created_at: datetime
    updated_at: datetime
    origin: AIOrigin
    personalization: None = None
    finalized_at: None = None
    archived_at: None = None
    pages: Annotated[tuple[AITextBookPage, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def coherent_initial_projection(self) -> "AITextBookProjection":
        if (self.direction != {"he": "rtl", "en": "ltr"}[self.language]
                or self.page_count != len(self.pages)
                or tuple(page.position for page in self.pages) != tuple(range(1, self.page_count + 1))
                or len({page.page_id for page in self.pages}) != self.page_count
                or len({page.source_page_key for page in self.pages}) != self.page_count):
            raise ValueError("Invalid canonical page structure")
        if (self.created_at.utcoffset() != timedelta(0) or self.updated_at != self.created_at):
            raise ValueError("Initial timestamps must match and be UTC")
        if any((page.document.blocks[0].language, page.document.blocks[0].direction)
               != (self.language, self.direction) for page in self.pages):
            raise ValueError("Page language must match Book")
        return self


class ProjectionContext(ProjectionContract):
    """Trusted composition input, never a client ownership claim or auth system.

    Backend must supply verified scope and immutable issuance ownership. This
    module can check their consistency, not prove possession of credentials.
    """

    operation_id: UUID
    generation_id: UUID
    book_id: UUID
    source_request_id: Label
    operation_owner_id: UUID
    source_owner_id: UUID
    book_owner_id: UUID
    authorized_owner_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    created_at: datetime

    @model_validator(mode="after")
    def utc_timestamp(self) -> "ProjectionContext":
        if self.created_at.utcoffset() != timedelta(0):
            raise ValueError("Timestamp must be UTC")
        return self
