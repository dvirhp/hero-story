"""Shared Book/Page DTOs; AI projection is supplied by Agent 1, not implemented here."""

from datetime import datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from storyforge.domain.base import Label, Language, PositiveInt
from storyforge.domain.documents import DocumentContract, ImageBlock, Key, PageDocument
from storyforge.domain.story_v2 import BookConstraints


class AssetBinding(DocumentContract):
    slot_key: Key
    asset_id: UUID


class PageInput(DocumentContract):
    document: PageDocument
    asset_bindings: tuple[AssetBinding, ...] = ()

    @model_validator(mode="after")
    def exact_bindings(self) -> "PageInput":
        slots = tuple(block.slot_key for block in self.document.blocks if isinstance(block, ImageBlock))
        bindings = tuple(binding.slot_key for binding in self.asset_bindings)
        if len(set(bindings)) != len(bindings) or set(slots) != set(bindings):
            raise ValueError("Image slots require exactly matching asset bindings")
        return self


class BookPage(PageInput):
    page_id: UUID
    position: PositiveInt
    source_page_key: Label | None = None
    source_target_id: Label | None = None


class BookOrigin(DocumentContract):
    generation_id: UUID | None = None
    template_version_id: UUID | None = None
    page_variant_id: Key | None = None
    source_display: Label | None = None


class BookDetail(DocumentContract):
    schema_version: Literal["1"] = "1"
    book_id: UUID
    creation_mode: Literal["AI_GENERATED", "TEMPLATE_BASED", "MANUAL"]
    state: Literal["draft", "finalized", "archived"] = "draft"
    revision: PositiveInt = 1
    title: Label
    language: Language
    direction: Literal["ltr", "rtl"]
    page_count: Annotated[int, Field(ge=0)]
    created_at: datetime
    updated_at: datetime
    origin: BookOrigin = BookOrigin()
    # A real version-validated personalization contract arrives with the catalog milestone.
    personalization: None = None
    finalized_at: datetime | None = None
    archived_at: datetime | None = None
    pages: tuple[BookPage, ...] = ()

    @model_validator(mode="after")
    def coherent_book(self) -> "BookDetail":
        if self.direction != {"en": "ltr", "he": "rtl"}[self.language]:
            raise ValueError("Direction must match language")
        times = (self.created_at, self.updated_at, self.finalized_at, self.archived_at)
        if any(value is not None and value.utcoffset() != timedelta(0) for value in times):
            raise ValueError("Book timestamps must be timezone-aware UTC")
        if self.updated_at < self.created_at:
            raise ValueError("Book timestamp order invalid")
        if self.page_count != len(self.pages) or tuple(page.position for page in self.pages) != tuple(range(1, self.page_count + 1)):
            raise ValueError("Pages must be complete, ordered and contiguous")
        if len({page.page_id for page in self.pages}) != self.page_count:
            raise ValueError("Page identities must be unique")
        origin = self.origin
        if self.creation_mode == "AI_GENERATED":
            if origin.generation_id is None or any((origin.template_version_id, origin.page_variant_id, origin.source_display)):
                raise ValueError("AI origin requires only generation identity")
            if self.revision == 1 and (not self.pages or any(page.source_page_key is None for page in self.pages)):
                raise ValueError("Initial AI pages require source identities")
            keys = tuple(page.source_page_key for page in self.pages if page.source_page_key is not None)
            if any(str(page.page_id) == page.source_page_key for page in self.pages):
                raise ValueError("AI pages require separate source identities")
            if len(set(keys)) != len(keys):
                raise ValueError("Source page identities must be unique")
        elif self.creation_mode == "MANUAL":
            if any((origin.generation_id, origin.template_version_id, origin.page_variant_id, origin.source_display)):
                raise ValueError("Manual Book cannot claim a source")
            if any(page.source_page_key is not None or page.source_target_id is not None for page in self.pages):
                raise ValueError("Manual pages cannot claim AI provenance")
        elif origin.generation_id is not None or origin.template_version_id is None or origin.page_variant_id is None:
            raise ValueError("Template origin requires version and variant")
        if self.state == "draft" and (self.finalized_at is not None or self.archived_at is not None):
            raise ValueError("Draft cannot have terminal timestamps")
        if self.state == "finalized" and (not self.pages or self.finalized_at is None or self.archived_at is not None):
            raise ValueError("Finalized Book requires pages and finalization time")
        if self.state == "archived" and self.archived_at is None:
            raise ValueError("Archived Book requires archive time")
        if any(value is not None and not self.created_at <= value <= self.updated_at for value in (self.finalized_at, self.archived_at)):
            raise ValueError("Lifecycle timestamp order invalid")
        return self


class ManualBookCreate(DocumentContract):
    schema_version: Literal["1"] = "1"
    title: Label
    language: Language
    pages: tuple[PageInput, ...] = ()


class AISourceSnapshot(DocumentContract):
    schema_version: Literal["1"] = "1"
    profile_id: Label
    profile_version: Label
    policy_version: Label
    quality_check_version: Label
    rubric_version: Label
    resolved_constraints: BookConstraints

    @model_validator(mode="after")
    def consistent_policy(self) -> "AISourceSnapshot":
        if self.resolved_constraints.policy_version != self.policy_version:
            raise ValueError("Source snapshot policy must match resolved constraints")
        return self


class AssetReference(DocumentContract):
    """Internal provisioned media metadata. No fetching, bytes or caller URLs."""
    asset_id: UUID
    storage_backend: Literal["local", "object_store"]
    object_key: Annotated[str, Field(pattern=r"^objects/[0-9a-f-]{36}\.(png|jpg|webp)$")]
    checksum: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    media_type: Literal["image/png", "image/jpeg", "image/webp"]
    byte_size: PositiveInt
    width: PositiveInt
    height: PositiveInt
    scope: Literal["public_editorial", "private"] = "private"
    state: Literal["ready", "blocked"] = "ready"

    @model_validator(mode="after")
    def opaque_key(self) -> "AssetReference":
        extensions = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
        if self.object_key != f"objects/{self.asset_id}.{extensions[self.media_type]}":
            raise ValueError("Asset key must be opaque and match media identity")
        return self


# Canonical detached aggregate and API detail are the same strict representation.
Book = BookDetail
