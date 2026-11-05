"""Portable SQLAlchemy schema; PostgreSQL is the deployment target."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class StoryRecord(Base):
    __tablename__ = "stories"
    __table_args__ = (
        CheckConstraint("status IN ('pending','processing','completed','failed')", name="ck_story_status"),
        CheckConstraint("age_months >= 0", name="ck_story_age"),
        CheckConstraint("page_count > 0", name="ck_story_count"),
        CheckConstraint("language IN ('en','he')", name="ck_story_language"),
        CheckConstraint("story_type IN ('general','bedtime','adventure','educational','alphabet')", name="ck_story_type"),
        CheckConstraint("(status = 'completed' AND content IS NOT NULL) OR (status <> 'completed' AND content IS NULL)", name="ck_story_content"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    child_name: Mapped[str] = mapped_column(String(40))
    age_months: Mapped[int] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String(16))
    page_count: Mapped[int] = mapped_column(Integer)
    story_type: Mapped[str] = mapped_column(String(32))
    theme: Mapped[str] = mapped_column(String(120))
    request_metadata: Mapped[dict] = mapped_column(JSON)
    schema_version: Mapped[str] = mapped_column(String(32), default="2")
    policy_version: Mapped[str] = mapped_column(String(120))
    content: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    generation_metadata: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


class StoryPageRecord(Base):
    __tablename__ = "story_pages"
    __table_args__ = (
        CheckConstraint("page_number > 0", name="ck_page_number"),
        UniqueConstraint("story_id", "page_id", name="uq_page_id"),
    )
    story_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True)
    page_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[str] = mapped_column(String(120))
    target_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sentence_units: Mapped[list] = mapped_column(JSON)
