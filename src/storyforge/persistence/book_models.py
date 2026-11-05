"""Milestone 1 relational storage. No ownership/access API is implied."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (JSON, BigInteger, CheckConstraint, DateTime, ForeignKey,
                        ForeignKeyConstraint, Index, Integer, String, UniqueConstraint, Uuid, func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from storyforge.persistence.models import Base

JsonDocument = JSON().with_variant(JSONB(), "postgresql")


class AssetRecord(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("storage_backend", "object_key", name="uq_asset_object"),
        CheckConstraint("storage_backend IN ('local','object_store')", name="ck_asset_backend"),
        CheckConstraint("scope IN ('public_editorial','private')", name="ck_asset_scope"),
        CheckConstraint("state IN ('ready','blocked')", name="ck_asset_state"),
        CheckConstraint("media_type IN ('image/png','image/jpeg','image/webp')", name="ck_asset_type"),
        CheckConstraint("byte_size > 0 AND width > 0 AND height > 0", name="ck_asset_size"),
        CheckConstraint("length(checksum) = 64", name="ck_asset_checksum"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    storage_backend: Mapped[str] = mapped_column(String(32))
    object_key: Mapped[str] = mapped_column(String(160))
    checksum: Mapped[str] = mapped_column(String(64))
    media_type: Mapped[str] = mapped_column(String(32))
    byte_size: Mapped[int] = mapped_column(BigInteger)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    scope: Mapped[str] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BookRecord(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("creation_mode IN ('AI_GENERATED','MANUAL')", name="ck_book_mode_m1"),
        CheckConstraint("state IN ('draft','finalized','archived')", name="ck_book_state"),
        CheckConstraint("revision >= 1", name="ck_book_revision"),
        CheckConstraint("schema_version = '1'", name="ck_book_schema"),
        CheckConstraint("length(title) BETWEEN 1 AND 120 AND length(trim(title)) > 0", name="ck_book_title"),
        CheckConstraint("(language = 'en' AND direction = 'ltr') OR (language = 'he' AND direction = 'rtl')", name="ck_book_direction"),
        CheckConstraint("(creation_mode = 'MANUAL' AND source_story_id IS NULL AND source_snapshot IS NULL) OR (creation_mode = 'AI_GENERATED' AND source_story_id IS NOT NULL AND source_snapshot IS NOT NULL)", name="ck_book_origin"),
        CheckConstraint("updated_at >= created_at", name="ck_book_time_order"),
        CheckConstraint("finalized_at IS NULL OR (finalized_at >= created_at AND finalized_at <= updated_at)", name="ck_book_finalized_time"),
        CheckConstraint("archived_at IS NULL OR (archived_at >= created_at AND archived_at <= updated_at)", name="ck_book_archived_time"),
        CheckConstraint("(state = 'draft' AND finalized_at IS NULL AND archived_at IS NULL) OR (state = 'finalized' AND finalized_at IS NOT NULL AND archived_at IS NULL) OR (state = 'archived' AND archived_at IS NOT NULL)", name="ck_book_lifecycle_time"),
        Index("ix_books_created", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    schema_version: Mapped[str] = mapped_column(String(16))
    creation_mode: Mapped[str] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(16))
    revision: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(120))
    language: Mapped[str] = mapped_column(String(16))
    direction: Mapped[str] = mapped_column(String(3))
    source_story_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("stories.id", ondelete="RESTRICT"), unique=True)
    source_snapshot: Mapped[dict | None] = mapped_column(JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BookPageRecord(Base):
    __tablename__ = "book_pages"
    __table_args__ = (
        UniqueConstraint("book_id", "position", name="uq_book_page_position", deferrable=True,
                         initially="IMMEDIATE", info={"dialect": "postgresql"}).ddl_if(dialect="postgresql"),
        UniqueConstraint("book_id", "position", name="uq_book_page_position_sqlite",
                         info={"dialect": "sqlite"}).ddl_if(dialect="sqlite"),
        UniqueConstraint("book_id", "id", name="uq_book_page_identity"),
        UniqueConstraint("book_id", "source_page_key", name="uq_book_source_page"),
        CheckConstraint("position > 0", name="ck_book_page_position"),
        CheckConstraint("document_schema_version = '1'", name="ck_book_page_schema"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    book_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("books.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    document_schema_version: Mapped[str] = mapped_column(String(16))
    document: Mapped[dict] = mapped_column(JsonDocument)
    source_page_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_target_id: Mapped[str | None] = mapped_column(String(120), nullable=True)


class BookPageAssetRecord(Base):
    __tablename__ = "book_page_assets"
    __table_args__ = (ForeignKeyConstraint(["book_id", "page_id"], ["book_pages.book_id", "book_pages.id"], ondelete="CASCADE"),)
    book_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    page_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    slot_key: Mapped[str] = mapped_column(String(120), primary_key=True)
    asset_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("assets.id", ondelete="RESTRICT"), index=True)
