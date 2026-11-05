"""Offline repository and real migration tests; no providers or network."""
import asyncio
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event, select, update
from sqlalchemy.exc import IntegrityError
from storyforge.persistence.database import create_database
from storyforge.persistence.models import Base, StoryRecord, StoryPageRecord
from storyforge.persistence.repository import InvalidTransition, SqlAlchemyStoryRepository
from storyforge.domain.story_v2 import StoryRequestV2, StoryV2
from storyforge.domain.generation_v2 import GenerationSuccessV2
from storyforge.domain.generation import GenerationFailure, GenerationError, QualityReport, UsageSummary
from storyforge.development.v2 import load_profiles_v2
from storyforge.validation.normalization_v2 import normalize_v2
from storyforge.llm.fixtures_v2 import fixture_steps_v2


def book(language="en"):
    req = StoryRequestV2(language=language, display_name="Or", age_months=0, page_count=2, theme="Night")
    brief = normalize_v2(req, load_profiles_v2())
    story = StoryV2.model_validate_json(fixture_steps_v2(brief)[1].response_json)
    result = GenerationSuccessV2(request_id="synthetic", story=story, quality=QualityReport(
        passed=True, check_version="test", rubric_version="test"), resolved_constraints=brief.constraints,
        usage=UsageSummary(), total_latency_seconds=0.1)
    return brief, result


async def setup():
    engine, sessions = create_database("sqlite+aiosqlite:///:memory:")
    @event.listens_for(engine.sync_engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, sessions, SqlAlchemyStoryRepository(sessions)


@pytest.mark.parametrize("language", ["en", "he"])
def test_lifecycle_and_order(language, run_async):
    async def run():
        engine, sessions, repo = await setup()
        try:
            brief, result = book(language)
            ident = await repo.create(brief)
            assert (await repo.get(ident)).status == "pending"
            async with sessions() as session:
                row = await session.get(StoryRecord, ident)
                assert row.created_at and row.age_months == 0
            await repo.start(ident)
            await repo.complete(ident, brief, result)
            saved = await repo.get(ident)
            assert saved.status == "completed"
            assert [p["page_number"] for p in saved.pages] == [1, 2]
            assert saved.content == result.story.model_dump(mode="json", exclude={"pages"})
            assert "error" not in str(saved.generation_metadata)
            with pytest.raises(InvalidTransition):
                await repo.complete(ident, brief, result)
            assert await repo.get(uuid4()) is None
        finally:
            await engine.dispose()
    run_async(run())


def test_failure_has_no_content_and_terminal_state(run_async):
    async def run():
        engine, _, repo = await setup()
        try:
            brief, result = book()
            ident = await repo.create(brief)
            with pytest.raises(InvalidTransition):
                await repo.complete(ident, brief, result)
            await repo.start(ident)
            failure = GenerationFailure(request_id="synthetic", usage=UsageSummary(), total_latency_seconds=1.,
                error=GenerationError(code="QUALITY_REJECTED", stage="quality", retryable=False,
                                      message="PRIVATE RAW ERROR MUST NOT BE STORED"))
            await repo.fail(ident, failure)
            saved = await repo.get(ident)
            assert saved.status == "failed" and saved.content is None and saved.pages == ()
            assert "PRIVATE" not in str(saved.generation_metadata)
            with pytest.raises(InvalidTransition):
                await repo.complete(ident, brief, result)
        finally:
            await engine.dispose()
    run_async(run())


def test_constraints_and_completion_transaction_rollback(run_async):
    async def run():
        engine, sessions, repo = await setup()
        try:
            brief, result = book()
            ident = await repo.create(brief)
            for values in ({"age_months": -1}, {"page_count": 0}, {"status": "other"},
                           {"status": "completed"}, {"language": "xx"}):
                with pytest.raises(IntegrityError):
                    async with sessions.begin() as session:
                        await session.execute(update(StoryRecord).where(StoryRecord.id == ident).values(**values))
            await repo.start(ident)
            # Force a page-key conflict after the status update: the entire completion must roll back.
            async with sessions.begin() as session:
                session.add(StoryPageRecord(story_id=ident, page_number=1, page_id="conflict", sentence_units=["test"]))
            with pytest.raises(IntegrityError):
                await repo.complete(ident, brief, result)
            saved = await repo.get(ident)
            assert saved.status == "processing" and saved.content is None and saved.generation_metadata is None
            with pytest.raises(IntegrityError):
                async with sessions.begin() as session:
                    session.add(StoryPageRecord(story_id=uuid4(), page_number=1, page_id="orphan", sentence_units=["test"]))
        finally:
            await engine.dispose()
    run_async(run())


def test_mismatched_request_rejected(run_async):
    async def run():
        engine, _, repo = await setup()
        try:
            brief, result = book()
            ident = await repo.create(brief)
            await repo.start(ident)
            changed = brief.model_copy(update={"request": brief.request.model_copy(update={"theme": "Other"})})
            with pytest.raises(InvalidTransition):
                await repo.complete(ident, changed, result)
            assert (await repo.get(ident)).status == "processing"
        finally:
            await engine.dispose()
    run_async(run())


def test_migration_upgrade_downgrade_and_schema_drift(tmp_path, monkeypatch, run_async):
    monkeypatch.setattr(asyncio, "run", run_async)
    monkeypatch.setenv("STORYFORGE_DATABASE_URL", "sqlite+aiosqlite:///" + (tmp_path / "migration.db").as_posix())
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.check(config)
    command.downgrade(config, "base")
    command.upgrade(config, "head")


def test_postgresql_migration_sql_compiles():
    import io
    output = io.StringIO()
    command.upgrade(Config("alembic.ini", output_buffer=output), "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE stories" in sql and "UUID" in sql and "ON DELETE CASCADE" in sql


def test_rejected_or_partial_success_cannot_be_persisted(run_async):
    async def run():
        engine, _, repo = await setup()
        try:
            brief, result = book()
            ident = await repo.create(brief)
            await repo.start(ident)
            from storyforge.domain.generation import QualityIssue
            rejected = result.model_copy(update={"quality": QualityReport(passed=False,
                issues=(QualityIssue(code="unsafe", severity="terminal", guidance="Rejected"),),
                check_version="test", rubric_version="test")})
            partial = result.model_copy(update={"story": result.story.model_copy(update={"pages": result.story.pages[:1]})})
            failed = GenerationFailure(request_id="failed", usage=UsageSummary(), total_latency_seconds=0.,
                error=GenerationError(code="QUALITY_REJECTED", stage="quality", retryable=False, message="Rejected"))
            for invalid in (rejected, partial, failed):
                with pytest.raises(ValueError):
                    await repo.complete(ident, brief, invalid)
            saved = await repo.get(ident)
            assert saved.status == "processing" and saved.content is None and saved.pages == ()
        finally:
            await engine.dispose()
    run_async(run())


def test_database_logging_and_personal_data_minimization(run_async, caplog):
    async def run():
        engine, sessions, repo = await setup()
        try:
            assert engine.echo is False and engine.sync_engine.hide_parameters is True
            brief, _ = book()
            secret = "private-guidance-canary"
            request = brief.request.model_copy(update={"guidance": secret, "interests": ("private-interest",)})
            brief = brief.model_copy(update={"request": request})
            ident = await repo.create(brief)
            async with sessions() as session:
                row = await session.get(StoryRecord, ident)
                assert row.child_name == request.display_name
                assert set(row.request_metadata) == {"text_density", "structure", "requested_title"}
                assert secret not in str(row.request_metadata)
            with pytest.raises(IntegrityError) as caught:
                async with sessions.begin() as session:
                    await session.execute(update(StoryRecord).where(StoryRecord.id == ident).values(age_months=-1, theme=secret))
            assert secret not in str(caught.value)
            assert secret not in caplog.text and "private-interest" not in caplog.text
            if engine.url.password:
                assert engine.url.password not in caplog.text
            if engine.url.password:
                assert "***" in str(engine.url)
        finally:
            await engine.dispose()
    run_async(run())
