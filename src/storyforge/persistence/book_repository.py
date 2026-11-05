"""Transaction-bound internal Book repository. No authorization facade or public routes."""

import json
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from storyforge.domain.book_capacity import AITextCapacityPolicy, BookCapacityPolicy
from storyforge.domain.book_errors import BookConflict, InvalidBook, checked
from storyforge.domain.books import AISourceSnapshot, AssetReference, BookDetail, ManualBookCreate
from storyforge.persistence.book_models import AssetRecord, BookPageAssetRecord, BookPageRecord, BookRecord
from storyforge.persistence.models import StoryPageRecord, StoryRecord


def utc(value: datetime) -> datetime:
    # SQLite drops timezone info; every write was validated as UTC before storage.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class SessionBookRepository:
    def __init__(self, session: AsyncSession, policy: BookCapacityPolicy, ai_policy: AITextCapacityPolicy):
        self._session, self.policy, self.ai_policy = session, policy, ai_policy

    def _active(self) -> None:
        if not self._session.in_transaction():
            raise RuntimeError("Book unit of work is not active")

    async def register_asset(self, asset: AssetReference) -> None:
        self._active()
        asset = checked(AssetReference, asset)
        values = asset.model_dump(exclude={"asset_id"})
        self._session.add(AssetRecord(id=asset.asset_id, **values))
        await self._session.flush()

    async def _validate_source(self, book: BookDetail, snapshot: AISourceSnapshot) -> None:
        self.ai_policy.validate_book(book)
        source = await self._session.scalar(select(StoryRecord).where(
            StoryRecord.id == book.origin.generation_id).with_for_update(read=True))
        if source is None or source.status != "completed" or source.content is None:
            raise InvalidBook()
        header, metadata = source.content, source.generation_metadata or {}
        if ((book.title, book.language, book.direction, book.page_count) !=
                (header.get("title"), source.language, header.get("direction"), source.page_count)
                or (snapshot.profile_id, snapshot.profile_version, snapshot.policy_version) !=
                (header.get("profile_id"), header.get("profile_version"), source.policy_version)
                or snapshot.resolved_constraints.page_count != book.page_count
                or snapshot.quality_check_version != metadata.get("quality_check_version")
                or snapshot.rubric_version != metadata.get("rubric_version")):
            raise InvalidBook()
        pages = (await self._session.scalars(select(StoryPageRecord).where(
            StoryPageRecord.story_id == source.id).order_by(StoryPageRecord.page_number))).all()
        # Integrity comparison only: Agent 1 owns constructing the actual projection.
        if len(pages) != book.page_count or any(
            (page.position, page.source_page_key, page.source_target_id,
             tuple(page.document.blocks[0].sentence_units)) !=
            (source_page.page_number, source_page.page_id, source_page.target_id,
             tuple(source_page.sentence_units))
            for page, source_page in zip(book.pages, pages)
        ):
            raise InvalidBook()

    async def add(self, book: BookDetail, snapshot: AISourceSnapshot | None = None) -> None:
        self._active()
        book = checked(BookDetail, book)
        self.policy.validate_book(book)
        if book.state != "draft" or book.revision != 1 or book.created_at != book.updated_at:
            raise InvalidBook()
        if book.creation_mode == "TEMPLATE_BASED":
            raise InvalidBook()  # Real template FKs/validation arrive in milestone 3.
        if book.creation_mode == "AI_GENERATED":
            if snapshot is None:
                raise InvalidBook()
            snapshot = checked(AISourceSnapshot, snapshot)
            await self._validate_source(book, snapshot)
        elif snapshot is not None:
            raise InvalidBook()
        asset_ids = {binding.asset_id for page in book.pages for binding in page.asset_bindings}
        if asset_ids:
            ready = set(await self._session.scalars(select(AssetRecord.id).where(
                AssetRecord.id.in_(asset_ids), AssetRecord.state == "ready").with_for_update(read=True)))
            if ready != asset_ids:
                raise InvalidBook()
        self._session.add(BookRecord(
            id=book.book_id, schema_version=book.schema_version, creation_mode=book.creation_mode,
            state=book.state, revision=book.revision, title=book.title, language=book.language,
            direction=book.direction, source_story_id=book.origin.generation_id,
            source_snapshot=snapshot.model_dump(mode="json") if snapshot else None,
            created_at=book.created_at, updated_at=book.updated_at,
            finalized_at=book.finalized_at, archived_at=book.archived_at,
        ))
        # Explicit flushes give deterministic FK ordering without implicit ORM relationships.
        await self._session.flush()
        self._session.add_all([BookPageRecord(
            id=page.page_id, book_id=book.book_id, position=page.position,
            document_schema_version=page.document.schema_version,
            document=page.document.model_dump(mode="json"), source_page_key=page.source_page_key,
            source_target_id=page.source_target_id,
        ) for page in book.pages])
        await self._session.flush()
        self._session.add_all([BookPageAssetRecord(
            book_id=book.book_id, page_id=page.page_id, slot_key=binding.slot_key,
            asset_id=binding.asset_id,
        ) for page in book.pages for binding in page.asset_bindings])
        await self._session.flush()

    async def get(self, book_id: UUID) -> BookDetail | None:
        self._active()
        if not isinstance(book_id, UUID):
            raise InvalidBook()
        row = await self._session.scalar(select(BookRecord).where(
            BookRecord.id == book_id).with_for_update(read=True))
        if row is None:
            return None
        pages = (await self._session.scalars(select(BookPageRecord).where(
            BookPageRecord.book_id == book_id).order_by(BookPageRecord.position))).all()
        bindings = (await self._session.scalars(select(BookPageAssetRecord).where(
            BookPageAssetRecord.book_id == book_id).order_by(BookPageAssetRecord.page_id, BookPageAssetRecord.slot_key))).all()
        by_page: dict[UUID, list[dict]] = {}
        for binding in bindings:
            by_page.setdefault(binding.page_id, []).append({"slot_key": binding.slot_key, "asset_id": str(binding.asset_id)})
        data = {
            "schema_version": row.schema_version, "book_id": str(row.id), "creation_mode": row.creation_mode,
            "state": row.state, "revision": row.revision, "title": row.title, "language": row.language,
            "direction": row.direction, "page_count": len(pages),
            "created_at": utc(row.created_at).isoformat(), "updated_at": utc(row.updated_at).isoformat(),
            "finalized_at": utc(row.finalized_at).isoformat() if row.finalized_at else None,
            "archived_at": utc(row.archived_at).isoformat() if row.archived_at else None,
            "origin": {"generation_id": str(row.source_story_id) if row.source_story_id else None},
            "pages": [{"page_id": str(page.id), "position": page.position, "document": page.document,
                       "asset_bindings": by_page.get(page.id, []), "source_page_key": page.source_page_key,
                       "source_target_id": page.source_target_id} for page in pages],
        }
        try:
            book = BookDetail.model_validate_json(json.dumps(data, ensure_ascii=False, allow_nan=False))
        except (ValidationError, ValueError, TypeError):
            raise InvalidBook() from None
        self.policy.validate_book(book)
        return book

    async def update_title(self, book_id: UUID, expected_revision: int, title: str, now: datetime) -> BookDetail:
        self._active()
        if (not isinstance(book_id, UUID) or type(expected_revision) is not int
                or expected_revision < 1 or not isinstance(now, datetime)
                or now.utcoffset() != UTC.utcoffset(now)):
            raise InvalidBook()
        row = await self._session.scalar(select(BookRecord).where(BookRecord.id == book_id).with_for_update())
        if row is None or row.state != "draft" or row.revision != expected_revision:
            raise BookConflict()
        try:
            title = ManualBookCreate(title=title, language=row.language).title
        except (ValidationError, ValueError):
            raise InvalidBook() from None
        row.title, row.revision, row.updated_at = title, row.revision + 1, max(now, utc(row.updated_at))
        await self._session.flush()
        book = await self.get(book_id)
        assert book is not None
        return book
