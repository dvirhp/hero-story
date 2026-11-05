"""Typed internal persistence ports; sessions never cross into application code."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from storyforge.domain.books import AISourceSnapshot, AssetReference, BookDetail
from storyforge.domain.generation_v2 import GenerationSuccessV2
from storyforge.domain.story_v2 import NormalizedBriefV2


class BookRepository(Protocol):
    async def add(self, book: BookDetail, snapshot: AISourceSnapshot | None = None) -> None: ...
    async def get(self, book_id: UUID) -> BookDetail | None: ...
    async def update_title(self, book_id: UUID, expected_revision: int, title: str, now: datetime) -> BookDetail: ...
    async def register_asset(self, asset: AssetReference) -> None: ...


class BookUnitOfWork(Protocol):
    books: BookRepository

    async def __aenter__(self) -> "BookUnitOfWork": ...
    async def __aexit__(self, exc_type, exc_value, traceback) -> bool | None: ...
    async def complete_story(self, story_id: UUID, brief: NormalizedBriefV2, result: GenerationSuccessV2) -> None: ...
