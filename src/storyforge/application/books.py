"""Internal milestone-1 services. Not safe to expose without milestone-2 ownership."""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from storyforge.application.ports import BookUnitOfWork
from storyforge.domain.books import AISourceSnapshot, BookDetail, BookPage, ManualBookCreate
from storyforge.domain.book_errors import InvalidBook, checked
from storyforge.domain.generation_v2 import GenerationSuccessV2
from storyforge.domain.story_v2 import NormalizedBriefV2


class InternalBookService:
    def __init__(self, unit_of_work: Callable[[], BookUnitOfWork], *,
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC)):
        self.unit_of_work, self.clock = unit_of_work, clock

    async def create_manual(self, command: ManualBookCreate) -> BookDetail:
        command = checked(ManualBookCreate, command)
        now = self.clock()
        book = BookDetail(
            book_id=uuid4(), creation_mode="MANUAL", title=command.title,
            language=command.language, direction={"en": "ltr", "he": "rtl"}[command.language],
            created_at=now, updated_at=now, page_count=len(command.pages),
            pages=tuple(BookPage(page_id=uuid4(), position=index, **page.model_dump())
                        for index, page in enumerate(command.pages, 1)),
        )
        async with self.unit_of_work() as unit:
            await unit.books.add(book)
        return book

    async def get(self, book_id: UUID) -> BookDetail | None:
        async with self.unit_of_work() as unit:
            return await unit.books.get(book_id)

    async def update_title(self, book_id: UUID, expected_revision: int, title: str) -> BookDetail:
        async with self.unit_of_work() as unit:
            return await unit.books.update_title(book_id, expected_revision, title, self.clock())

    async def save_accepted_ai_projection(
        self, projection: BookDetail, brief: NormalizedBriefV2, result: GenerationSuccessV2,
    ) -> BookDetail:
        """Validate Agent 1's supplied projection; do not construct it or call an engine."""
        projection = checked(BookDetail, projection)
        brief = checked(NormalizedBriefV2, brief)
        result = checked(GenerationSuccessV2, result)
        if projection.creation_mode != "AI_GENERATED" or projection.origin.generation_id is None:
            raise InvalidBook()
        snapshot = AISourceSnapshot(
            profile_id=result.story.profile_id, profile_version=result.story.profile_version,
            policy_version=brief.constraints.policy_version, quality_check_version=result.quality.check_version,
            rubric_version=result.quality.rubric_version, resolved_constraints=result.resolved_constraints,
        )
        async with self.unit_of_work() as unit:
            await unit.complete_story(projection.origin.generation_id, brief, result)
            await unit.books.add(projection, snapshot)
        return projection
