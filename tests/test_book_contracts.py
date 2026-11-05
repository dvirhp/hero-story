"""Pure canonical contracts/capacity, including the independent Agent 1 wire fixture."""

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from canonical_helpers import ai_fixture, manual, manual_detail
from storyforge.api.book_dtos import BookDetailResponse, BookTitleUpdate, ManualBookCreateRequest
from storyforge.domain.book_capacity import AITextCapacityPolicy, BookCapacityPolicy, CapacityExceeded, canonical_json_bytes
from storyforge.domain.books import AssetBinding, AssetReference, BookDetail, PageInput
from storyforge.domain.documents import Frame, ImageBlock, Layout, PageDocument, TextBlock


def test_agent1_projection_wire_is_lossless_and_byte_compatible():
    _, _, book = ai_fixture()
    original = json.loads((Path(__file__).parent / "fixtures/canonical_ai_he_27.json").read_text(encoding="utf-8"))["projection"]
    assert json.loads(canonical_json_bytes(book)) == original
    assert len(canonical_json_bytes(book)) == len(json.dumps(original, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    AITextCapacityPolicy().validate_book(book)
    assert len(book.pages) == 27 and book.direction == "rtl"
    assert BookDetailResponse is BookDetail
    assert ManualBookCreateRequest.model_validate_json(manual().model_dump_json()) == manual()


@pytest.mark.parametrize("units", [(), ("",), (" ",), ("x\u202e",), ("x\ud800",)])
def test_bad_text_or_unicode_is_rejected(units):
    with pytest.raises(ValidationError):
        TextBlock(block_id="body", language="en", direction="ltr", sentence_units=units)


@pytest.mark.parametrize("changes", [{"direction":"rtl"}, {"url":"https://example.invalid"},
    {"html":"<script>"}, {"style":"arbitrary-css"}, {"block_id":"../../x"}])
def test_extra_and_executable_fields_are_rejected(changes):
    with pytest.raises(ValidationError):
        TextBlock(**dict(block_id="body", language="en", direction="ltr", sentence_units=("literal {{field}}",)) | changes)


@pytest.mark.parametrize("frame", [dict(x=0,y=0,width=0,height=1), dict(x=.9,y=0,width=.2,height=1),
    dict(x=0,y=0,width=float("nan"),height=1), dict(x="0",y=0,width=1,height=1)])
def test_frames_are_bounded(frame):
    with pytest.raises(ValidationError):
        Frame(**frame)


def test_future_illustrated_pages_are_supported_without_ai_text_restrictions():
    asset_id = uuid4()
    text = TextBlock(block_id="caption", language="en", direction="ltr", style="caption", sentence_units=("x" * 401,))
    image = ImageBlock(block_id="picture", slot_key="hero", frame=Frame(x=0.,y=0.,width=1.,height=1.))
    document = PageDocument(layout=Layout(preset="text-image-v1"), blocks=(text,image))
    page = PageInput(document=document, asset_bindings=(AssetBinding(slot_key="hero",asset_id=asset_id),))
    assert page.document.blocks[0].sentence_units[0] == "x" * 401
    BookCapacityPolicy().validate_document(document)
    with pytest.raises(ValidationError):
        PageInput(document=document)
    with pytest.raises(ValidationError):
        PageDocument(blocks=(image,))
    with pytest.raises(ValidationError):
        PageDocument(blocks=(text,text))


@pytest.mark.parametrize("field,value", [("position",0),("position",True)])
def test_bad_page_positions(field,value):
    page=manual_detail().pages[0]
    with pytest.raises(ValidationError):
        type(page).model_validate(dict(page.model_dump()) | {field:value})


@pytest.mark.parametrize("change", ["missing", "order", "identity", "count", "time", "origin"])
def test_book_structure_is_complete(change):
    raw=manual_detail().model_dump()
    if change=="missing":raw["pages"]=raw["pages"][:1]
    elif change=="order":raw["pages"]=tuple(reversed(raw["pages"]))
    elif change=="identity":raw["pages"][1]["page_id"]=raw["pages"][0]["page_id"]
    elif change=="count":raw["page_count"]=True
    elif change=="time":raw["created_at"]=datetime(2026,11,5)
    else:raw["origin"]["generation_id"]=uuid4()
    with pytest.raises(ValidationError):BookDetail.model_validate(raw)


def test_title_code_points_and_safe_title_dto():
    BookTitleUpdate(title="\U0001f319"*120)
    with pytest.raises(ValidationError):BookTitleUpdate(title="x"*121)
    with pytest.raises(ValidationError):BookTitleUpdate(title="ok",creation_mode="MANUAL")


def test_exact_utf8_page_and_book_size_boundaries():
    book=manual_detail()
    page_size=len(canonical_json_bytes(book.pages[0].document))
    size=len(canonical_json_bytes(book))
    BookCapacityPolicy(maximum_document_bytes=page_size,maximum_book_bytes=size).validate_book(book)
    with pytest.raises(CapacityExceeded):BookCapacityPolicy(maximum_document_bytes=page_size-1).validate_book(book)
    with pytest.raises(CapacityExceeded):BookCapacityPolicy(maximum_book_bytes=size-1).validate_book(book)


def test_ai_unit_count_and_length_boundaries_are_separate_from_general_document():
    _,_,book=ai_fixture()
    raw=book.model_dump(mode="json")
    raw["pages"][0]["document"]["blocks"][0]["sentence_units"]=["x"*400]*128
    valid=BookDetail.model_validate_json(json.dumps(raw))
    AITextCapacityPolicy().validate_book(valid)
    for units in (["x"]*129,["x"*401]):
        raw["pages"][0]["document"]["blocks"][0]["sentence_units"]=units
        broad=BookDetail.model_validate_json(json.dumps(raw))
        BookCapacityPolicy().validate_book(broad)
        with pytest.raises(CapacityExceeded):AITextCapacityPolicy().validate_book(broad)
    with pytest.raises(CapacityExceeded):AITextCapacityPolicy(maximum_pages=26).validate_book(book)
    AITextCapacityPolicy(maximum_pages=64).validate_book(book)


@pytest.mark.parametrize("changes", [{"maximum_pages":True},{"maximum_pages":0},
    {"maximum_document_bytes":262145},{"maximum_book_bytes":16777217},
    {"maximum_sentence_units":129},{"maximum_unit_code_points":401}])
def test_invalid_ai_policy(changes):
    with pytest.raises(ValidationError):AITextCapacityPolicy(**changes)


def test_draft_after_initial_ai_projection_can_gain_manual_or_illustrated_pages():
    _,_,book=ai_fixture()
    from storyforge.domain.books import BookPage
    manual_page=BookPage(page_id=uuid4(),position=28,document=manual().pages[0].document)
    edited=book.model_copy(update={"revision":2,"page_count":28,"pages":book.pages+(manual_page,)})
    BookDetail.model_validate_json(edited.model_dump_json())
    # Initial projection still cannot silently omit original source identity.
    with pytest.raises(ValidationError):BookDetail.model_validate_json(edited.model_copy(update={"revision":1}).model_dump_json())


def test_default_general_document_byte_limit_has_no_text_only_assumption():
    document=PageDocument(blocks=(TextBlock(block_id="body",language="en",direction="ltr",
        sentence_units=("x"*12000,)*23),))
    with pytest.raises(CapacityExceeded):BookCapacityPolicy().validate_document(document)


def test_asset_refs_are_opaque_metadata_not_urls_or_binary_data():
    ident=uuid4()
    values=dict(asset_id=ident,storage_backend="local",object_key=f"objects/{ident}.png",checksum="0"*64,
                media_type="image/png",byte_size=4,width=1,height=1)
    AssetReference(**values)
    for changes in ({"object_key":"https://private.invalid/x?token=x"},{"checksum":"x"},{"bytes":"secret"},
                    {"object_key":f"objects/{uuid4()}.png"}):
        with pytest.raises(ValidationError):AssetReference(**(values|changes))
