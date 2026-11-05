"""Canonical structured pages. Plain text and media references, never executable markup."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StringConstraints, model_validator

from storyforge.domain.base import Contract, Language
from storyforge.quality.text import forbidden_controls, string_values

Key = Annotated[str, StringConstraints(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")]
PlainText = Annotated[str, StringConstraints(min_length=1, max_length=12000, pattern=r"\S")]


class DocumentContract(Contract):
    model_config = ConfigDict(revalidate_instances="always", hide_input_in_errors=True)

    @model_validator(mode="after")
    def safe_unicode(self) -> "DocumentContract":
        if any(forbidden_controls(text) for text in string_values(self.model_dump())):
            raise ValueError("Unsupported Unicode controls")
        return self


class Frame(DocumentContract):
    x: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    y: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    width: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]
    height: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]

    @model_validator(mode="after")
    def within_page(self) -> "Frame":
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("Frame exceeds normalized page")
        return self


class Layout(DocumentContract):
    preset: Literal["text-only-v1", "text-image-v1"] = "text-only-v1"


class TextBlock(DocumentContract):
    kind: Literal["text"] = "text"
    block_id: Key
    language: Language
    direction: Literal["ltr", "rtl"]
    style: Literal["body", "title", "caption"] = "body"
    sentence_units: Annotated[tuple[PlainText, ...], Field(min_length=1, max_length=1024)]
    frame: Frame | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def matching_direction(self) -> "TextBlock":
        if self.direction != {"en": "ltr", "he": "rtl"}[self.language]:
            raise ValueError("Direction must match language")
        return self


class ImageBlock(DocumentContract):
    kind: Literal["image"] = "image"
    block_id: Key
    slot_key: Key
    fit: Literal["contain", "cover"] = "contain"
    alt: PlainText | None = None
    frame: Frame | None = Field(default=None, exclude_if=lambda value: value is None)


Block = Annotated[TextBlock | ImageBlock, Field(discriminator="kind")]


class PageDocument(DocumentContract):
    schema_version: Literal["1"] = "1"
    layout: Layout = Layout()
    blocks: Annotated[tuple[Block, ...], Field(min_length=1, max_length=256)]

    @model_validator(mode="after")
    def coherent_blocks(self) -> "PageDocument":
        if len({block.block_id for block in self.blocks}) != len(self.blocks):
            raise ValueError("Block identities must be unique")
        images = tuple(block for block in self.blocks if isinstance(block, ImageBlock))
        if self.layout.preset == "text-only-v1" and images:
            raise ValueError("Text-only layout cannot contain image blocks")
        if len({block.slot_key for block in images}) != len(images):
            raise ValueError("Image slots must be unique per page")
        return self
