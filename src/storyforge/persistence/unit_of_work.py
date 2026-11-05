"""Explicit one-session atomic scope; never attached to the current HTTP app."""

from types import TracebackType
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from storyforge.domain.book_capacity import AITextCapacityPolicy, BookCapacityPolicy
from storyforge.domain.generation_v2 import GenerationSuccessV2
from storyforge.domain.story_v2 import NormalizedBriefV2
from storyforge.persistence.book_repository import SessionBookRepository
from storyforge.persistence.repository import SqlAlchemyStoryRepository


class SqlAlchemyBookUnitOfWork:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], *,
                 policy: BookCapacityPolicy = BookCapacityPolicy(),
                 ai_policy: AITextCapacityPolicy = AITextCapacityPolicy()):
        self.sessions = sessions
        self.policy = BookCapacityPolicy.model_validate_json(policy.model_dump_json())
        self.ai_policy = AITextCapacityPolicy.model_validate_json(ai_policy.model_dump_json())
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "SqlAlchemyBookUnitOfWork":
        if self._session is not None:
            raise RuntimeError("Unit of work cannot be reused")
        self._session = self.sessions()
        self._transaction = self._session.begin()
        await self._transaction.__aenter__()
        self.books = SessionBookRepository(self._session, self.policy, self.ai_policy)
        return self

    async def complete_story(self, story_id: UUID, brief: NormalizedBriefV2, result: GenerationSuccessV2) -> None:
        if self._session is None or not self._session.in_transaction():
            raise RuntimeError("Book unit of work is not active")
        await SqlAlchemyStoryRepository(self.sessions)._complete_in_transaction(self._session, story_id, brief, result)

    async def __aexit__(self, exc_type: type[BaseException] | None,
                        exc_value: BaseException | None, traceback: TracebackType | None) -> bool | None:
        try:
            return await self._transaction.__aexit__(exc_type, exc_value, traceback)
        finally:
            await self._session.close()
