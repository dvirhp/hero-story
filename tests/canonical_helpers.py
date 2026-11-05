"""Synthetic canonical fixtures. Contains no AI projection implementation."""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from storyforge.domain.books import BookDetail, BookPage, ManualBookCreate, PageInput
from storyforge.domain.documents import PageDocument, TextBlock
from storyforge.domain.generation_v2 import GenerationSuccessV2
from storyforge.domain.story_v2 import NormalizedBriefV2

NOW = datetime(2026, 11, 5, 10, tzinfo=UTC)


def manual(pages=2, language="en") -> ManualBookCreate:
    return ManualBookCreate(title="Garden", language=language, pages=tuple(PageInput(document=PageDocument(
        blocks=(TextBlock(block_id="body", language=language, direction="rtl" if language == "he" else "ltr",
                          sentence_units=("\u05e9\u05b8\u05c1\u05dc\u05d5\u05b9\u05dd \U0001f319" if language == "he" else "Or sees a star.",)),)))
        for _ in range(pages)))


def manual_detail(pages=2) -> BookDetail:
    command = manual(pages)
    return BookDetail(book_id=uuid4(), creation_mode="MANUAL", title=command.title,
        language=command.language, direction="ltr", page_count=pages, created_at=NOW, updated_at=NOW,
        pages=tuple(BookPage(page_id=uuid4(), position=i, **page.model_dump()) for i, page in enumerate(command.pages, 1)))


def ai_fixture():
    # Captured output of Agent 1's pure projector; never substitute a local mapper.
    raw = json.loads((Path(__file__).parent / "fixtures/canonical_ai_he_27.json").read_text(encoding="utf-8"))
    return (NormalizedBriefV2.model_validate_json(json.dumps(raw["brief"], ensure_ascii=False)),
            GenerationSuccessV2.model_validate_json(json.dumps(raw["result"], ensure_ascii=False)),
            BookDetail.model_validate_json(json.dumps(raw["projection"], ensure_ascii=False)))
