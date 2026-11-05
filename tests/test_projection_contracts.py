"""Offline B1 structural ceilings, separate from legacy generation contracts."""

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from storyforge.projection.capacity import CapacityPolicy, canonical_json_bytes
from storyforge.projection.contracts import AIOrigin, AITextBlock, AITextBookPage, AITextBookProjection, AITextPageDocument


@pytest.mark.parametrize("language,direction", [("he", "rtl"), ("en", "ltr")])
def test_text_only_shape_preserves_unicode_and_units(language, direction):
    units = ("שָׁלוֹם 😀", "A quoted \\\"word\\\".")
    document = AITextPageDocument(blocks=(AITextBlock(
        language=language, direction=direction, sentence_units=units),))
    raw = json.loads(canonical_json_bytes(document))
    assert raw["schema_version"] == "1"
    assert raw["layout"] == {"preset": "text-only-v1"}
    assert raw["blocks"][0]["sentence_units"] == list(units)
    assert AITextPageDocument.model_validate_json(canonical_json_bytes(document)) == document


@pytest.mark.parametrize("changes", [
    {"maximum_story_pages": True}, {"maximum_story_pages": 0},
    {"maximum_story_pages": "32"}, {"maximum_title_code_points": 121},
    {"maximum_sentence_units": 129}, {"maximum_unit_code_points": 401},
    {"maximum_document_bytes": 262145}, {"maximum_book_bytes": 16777217},
    {"version": "future"}, {"unexpected": 1},
])
def test_invalid_capacity_config_is_rejected(changes):
    with pytest.raises(ValidationError):
        CapacityPolicy(**changes)


def test_product_page_limit_is_configurable_without_arbitrary_schema_ceiling():
    assert CapacityPolicy(maximum_story_pages=64).maximum_story_pages == 64


@pytest.mark.parametrize("units", [(), ("",), (" ",), ("x" * 401,), ("x",) * 129,
                                    ("x\ud800",), ("x\u202e",)])
def test_invalid_text_units_are_rejected(units):
    with pytest.raises(ValidationError):
        AITextBlock(language="en", direction="ltr", sentence_units=units)


def test_exact_unit_limits_and_new_page_identity():
    block = AITextBlock(language="en", direction="ltr", sentence_units=("x" * 400,) * 128)
    document = AITextPageDocument(blocks=(block,))
    with pytest.raises(ValidationError):
        AITextPageDocument(blocks=(block, block))
    with pytest.raises(ValidationError):
        AITextBookPage(page_id=UUID(int=1), position=1, document=document,
                       source_page_key=str(UUID(int=1)), source_target_id=None)


@pytest.mark.parametrize("changes", [{"direction": "rtl"}, {"kind": "image"},
                                      {"style": "title"}, {"url": "private"}])
def test_no_extra_layout_asset_or_direction_features(changes):
    with pytest.raises(ValidationError):
        AITextBlock(**dict(language="en", direction="ltr", sentence_units=("word",)) | changes)


def test_equal_instant_does_not_allow_non_utc_updated_timestamp():
    created = datetime(2026, 11, 5, tzinfo=timezone.utc)
    page = AITextBookPage(page_id=UUID(int=1), position=1, source_page_key="source", source_target_id=None,
        document=AITextPageDocument(blocks=(AITextBlock(language="en", direction="ltr", sentence_units=("word",)),)))
    with pytest.raises(ValidationError):
        AITextBookProjection(book_id=UUID(int=2), title="Night", language="en", direction="ltr", page_count=1,
            created_at=created, updated_at=created.astimezone(timezone(timedelta(hours=1))),
            origin=AIOrigin(generation_id=UUID(int=3)), pages=(page,))
