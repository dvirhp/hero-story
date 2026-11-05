"""Versioned canonical safety policy and exact, non-normalizing serialization."""

import json
from typing import Annotated, Literal

from pydantic import Field

from storyforge.domain.base import PositiveInt
from storyforge.projection.contracts import ProjectionContract


class CapacityPolicy(ProjectionContract):
    version: Literal["ai-text-document-v1"] = "ai-text-document-v1"
    # Product limit: raising it requires separate runtime admission, not graph edits.
    maximum_story_pages: PositiveInt = 32
    maximum_title_code_points: Annotated[int, Field(ge=1, le=120)] = 120
    maximum_sentence_units: Annotated[int, Field(ge=1, le=128)] = 128
    maximum_unit_code_points: Annotated[int, Field(ge=1, le=400)] = 400
    maximum_document_bytes: Annotated[int, Field(ge=1, le=262144)] = 262144
    maximum_book_bytes: Annotated[int, Field(ge=1, le=16777216)] = 16777216


class ProjectionError(ValueError):
    """Fixed categories only; no source content or validation inputs."""

    def __init__(self, code: Literal[
        "INPUT_INVALID", "UNAUTHORIZED", "SOURCE_MISMATCH", "SOURCE_NOT_ACCEPTED",
        "CAPACITY_EXCEEDED", "IDENTITY_CONFLICT",
    ]) -> None:
        self.code = code
        super().__init__(code)


def canonical_json_bytes(value: ProjectionContract) -> bytes:
    """Canonical representation used for all B1 byte admission/validation.

    Serialize the complete document/BookDetail, never an exclude-unset subset.
    """
    return json_bytes(value.model_dump(mode="json"))


def json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
