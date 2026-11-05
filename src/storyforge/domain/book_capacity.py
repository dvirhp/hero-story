"""Canonical capacity checks, not an AI-to-Book projector or age-based length policy."""

import json
from typing import Literal

from pydantic import Field

from storyforge.domain.base import PositiveInt
from storyforge.domain.books import BookDetail
from storyforge.domain.documents import DocumentContract, PageDocument, TextBlock


def canonical_json_bytes(value: DocumentContract) -> bytes:
    """Full DTO including nullable fields; compact UTF-8, no Unicode normalization."""
    return json.dumps(value.model_dump(mode="json"), ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


class CapacityExceeded(ValueError):
    def __init__(self) -> None:
        super().__init__("CANONICAL_CAPACITY_EXCEEDED")


class BookCapacityPolicy(DocumentContract):
    version: Literal["book-document-v1"] = "book-document-v1"
    # General storage policy is independent of the narrower AI text-only contract.
    maximum_pages: PositiveInt = 32
    maximum_document_bytes: PositiveInt = 256 * 1024
    maximum_book_bytes: PositiveInt = 16 * 1024 * 1024

    def validate_document(self, document: PageDocument) -> None:
        if len(canonical_json_bytes(document)) > self.maximum_document_bytes:
            raise CapacityExceeded()

    def validate_book(self, book: BookDetail) -> None:
        if book.page_count > self.maximum_pages or len(canonical_json_bytes(book)) > self.maximum_book_bytes:
            raise CapacityExceeded()
        for page in book.pages:
            self.validate_document(page.document)


class AITextCapacityPolicy(BookCapacityPolicy):
    version: Literal["ai-text-document-v1"] = "ai-text-document-v1"
    maximum_document_bytes: int = Field(default=256 * 1024, ge=1, le=256 * 1024)
    maximum_book_bytes: int = Field(default=16 * 1024 * 1024, ge=1, le=16 * 1024 * 1024)
    maximum_sentence_units: int = Field(default=128, ge=1, le=128)
    maximum_unit_code_points: int = Field(default=400, ge=1, le=400)

    def validate_book(self, book: BookDetail) -> None:
        super().validate_book(book)
        for page in book.pages:
            document = page.document
            if (document.layout.preset != "text-only-v1" or len(document.blocks) != 1
                    or not isinstance(document.blocks[0], TextBlock) or page.asset_bindings):
                raise CapacityExceeded()
            block = document.blocks[0]
            if (block.block_id != "body" or block.style != "body" or block.frame is not None
                    or (block.language, block.direction) != (book.language, book.direction)
                    or len(block.sentence_units) > self.maximum_sentence_units
                    or any(len(unit) > self.maximum_unit_code_points for unit in block.sentence_units)):
                raise CapacityExceeded()
