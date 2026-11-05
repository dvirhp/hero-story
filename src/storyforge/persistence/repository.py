"""Async unit of work. Each public mutation owns one atomic transaction."""
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from storyforge.domain.generation import GenerationFailure
from storyforge.domain.generation_v2 import GenerationSuccessV2
from storyforge.domain.story_v2 import NormalizedBriefV2
from storyforge.persistence.models import StoryRecord, StoryPageRecord


class InvalidTransition(ValueError):
    """Missing story or invalid/concurrent lifecycle transition (no child data)."""


@dataclass(frozen=True)
class SavedStory:
    id: UUID
    status: str
    content: dict | None
    pages: tuple[dict, ...]
    generation_metadata: dict | None


class StoryRepository(Protocol):
    async def create(self, brief: NormalizedBriefV2) -> UUID: ...
    async def start(self, story_id: UUID) -> None: ...
    async def complete(self, story_id: UUID, brief: NormalizedBriefV2, result: GenerationSuccessV2) -> None: ...
    async def fail(self, story_id: UUID, result: GenerationFailure) -> None: ...
    async def get(self, story_id: UUID) -> SavedStory | None: ...


def safe_metadata(result: GenerationSuccessV2 | GenerationFailure) -> dict:
    # Explicit allowlist: never serialize errors, provider diagnostics, prompts or drafts.
    return {
        "duration_seconds": result.total_latency_seconds,
        "known_estimated_cost_usd": result.usage.known_estimated_cost_usd,
        "upper_estimated_cost_usd": result.usage.upper_estimated_cost_usd,
        "has_unknown_usage": result.usage.has_unknown_usage,
        "has_unknown_cost": result.usage.has_unknown_cost,
        "attempts": [{key: attempt.model_dump(mode="json")[key] for key in (
            "stage", "attempt_number", "provider", "model", "prompt_version", "latency_seconds",
            "usage", "estimated_cost_usd", "reserved_cost_usd", "pricing_version", "outcome",
        )} for attempt in result.usage.attempts],
    }


class SqlAlchemyStoryRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        self.sessions = sessions

    async def create(self, brief: NormalizedBriefV2) -> UUID:
        brief = NormalizedBriefV2.model_validate_json(brief.model_dump_json())
        request = brief.request
        # Store only specified personalization and structured generation options;
        # freeform guidance, interests and pronouns are deliberately not retained.
        options = request.model_dump(mode="json", include={"text_density", "structure", "requested_title"})
        row = StoryRecord(child_name=request.display_name, age_months=request.age_months,
                          language=request.language, page_count=request.page_count,
                          story_type=request.story_type, theme=request.theme,
                          request_metadata=options, policy_version=brief.constraints.policy_version)
        async with self.sessions.begin() as session:
            session.add(row)
            await session.flush()
            return row.id

    async def _transition(self, session: AsyncSession, story_id: UUID, expected: str, **values) -> None:
        changed = await session.execute(update(StoryRecord).where(
            StoryRecord.id == story_id, StoryRecord.status == expected).values(**values))
        if changed.rowcount != 1:
            raise InvalidTransition("Story lifecycle transition unavailable")

    async def start(self, story_id: UUID) -> None:
        async with self.sessions.begin() as session:
            await self._transition(session, story_id, "pending", status="processing")

    async def complete(self, story_id: UUID, brief: NormalizedBriefV2, result: GenerationSuccessV2) -> None:
        # Revalidate at the persistence boundary, including contextual hard constraints.
        brief = NormalizedBriefV2.model_validate_json(brief.model_dump_json())
        result = GenerationSuccessV2.model_validate_json(result.model_dump_json())
        result.story.validate_for(brief)
        if result.resolved_constraints != brief.constraints:
            raise ValueError("Accepted constraints differ from request")
        async with self.sessions.begin() as session:
            row = await session.get(StoryRecord, story_id)
            if row is None or (row.child_name, row.age_months, row.language, row.page_count,
                               row.story_type, row.theme, row.policy_version, row.request_metadata) != (
                brief.request.display_name, brief.request.age_months, brief.request.language,
                brief.request.page_count, brief.request.story_type, brief.request.theme,
                brief.constraints.policy_version, brief.request.model_dump(mode="json", include={"text_density", "structure", "requested_title"})):
                raise InvalidTransition("Stored request does not match completion")
            content = result.story.model_dump(mode="json", exclude={"pages"})
            metadata = safe_metadata(result)
            metadata["quality_check_version"] = result.quality.check_version
            metadata["rubric_version"] = result.quality.rubric_version
            await self._transition(session, story_id, "processing", status="completed",
                                   content=content, generation_metadata=metadata)
            session.add_all([StoryPageRecord(story_id=story_id, **page.model_dump(mode="json"))
                             for page in result.story.pages])
            await session.flush()

    async def fail(self, story_id: UUID, result: GenerationFailure) -> None:
        result = GenerationFailure.model_validate_json(result.model_dump_json())
        async with self.sessions.begin() as session:
            await self._transition(session, story_id, "processing", status="failed",
                                   failure_code=result.error.code, generation_metadata=safe_metadata(result))

    async def get(self, story_id: UUID) -> SavedStory | None:
        async with self.sessions.begin() as session:
            # PostgreSQL READ COMMITTED takes a new snapshot per statement.
            # Hold a shared row lock until pages are read so a concurrent completion
            # cannot combine an old status/header with newly committed pages.
            row = await session.scalar(select(StoryRecord).where(
                StoryRecord.id == story_id).with_for_update(read=True))
            if row is None:
                return None
            pages = (await session.scalars(select(StoryPageRecord).where(
                StoryPageRecord.story_id == story_id).order_by(StoryPageRecord.page_number))).all()
            return SavedStory(row.id, row.status, row.content, tuple({
                "page_id": page.page_id, "page_number": page.page_number,
                "target_id": page.target_id, "sentence_units": page.sentence_units,
            } for page in pages), row.generation_metadata)
