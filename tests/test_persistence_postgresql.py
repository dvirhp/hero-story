"""Opt-in REAL PostgreSQL integration. Never substitutes SQLite or mocks."""
import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from storyforge.persistence.models import StoryRecord
from sqlalchemy.engine import make_url

import test_persistence as offline
from storyforge.config import AppSettings
from storyforge.development.v2 import load_profiles_v2
from storyforge.domain.generation import GenerationFailure, GenerationError, QualityReport, UsageSummary
from storyforge.domain.generation_v2 import GenerationSuccessV2
from storyforge.domain.story_v2 import StoryRequestV2, StoryV2
from storyforge.llm.fixtures_v2 import fixture_steps_v2
from storyforge.persistence.database import create_database
from storyforge.persistence.repository import InvalidTransition, SqlAlchemyStoryRepository
from storyforge.validation.normalization_v2 import normalize_v2

pytestmark = [pytest.mark.postgresql, pytest.mark.enable_socket, pytest.mark.allow_hosts(["127.0.0.1", "::1"])]


@pytest.fixture
def postgres(monkeypatch, run_async):
    raw = os.environ.get("STORYFORGE_TEST_POSTGRES_URL")
    if not raw:
        pytest.skip("Real PostgreSQL requires STORYFORGE_TEST_POSTGRES_URL; no SQLite fallback")
    url = make_url(raw)
    if url.drivername != "postgresql+asyncpg" or url.host != "127.0.0.1":
        pytest.fail("Integration database must use asyncpg on explicit IPv4 loopback", pytrace=False)
    # Never migrate/drop the supplied database: create a uniquely named disposable database.
    name = "storyforge_test_" + uuid4().hex
    admin, _ = create_database(url.set(database="postgres"))
    async def create():
        async with admin.connect() as connection:
            connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
            await connection.execute(text('CREATE DATABASE "' + name + '"'))
    run_async(create())
    engine, sessions = create_database(url.set(database=name))
    monkeypatch.setenv("STORYFORGE_DATABASE_URL", url.set(database=name).render_as_string(hide_password=False))
    monkeypatch.setattr(asyncio, "run", run_async)
    try:
        command.upgrade(Config("alembic.ini"), "head")
        async def setup():
            return engine, sessions, SqlAlchemyStoryRepository(sessions)
        monkeypatch.setattr(offline, "setup", setup)
        yield engine, sessions, SqlAlchemyStoryRepository(sessions)
    finally:
        async def cleanup():
            await engine.dispose()
            try:
                async with admin.connect() as connection:
                    connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
                    await connection.execute(text('DROP DATABASE "' + name + '" WITH (FORCE)'))
            finally:
                await admin.dispose()
        run_async(cleanup())


@pytest.mark.parametrize("language", ["he", "en"])
def test_postgres_create_retrieve_lifecycle(postgres, run_async, language):
    offline.test_lifecycle_and_order(language, run_async)


def test_postgres_atomic_completion_constraints_and_duplicate_numbers(postgres, run_async):
    offline.test_constraints_and_completion_transaction_rollback(run_async)


def test_postgres_failed_draft_has_no_content(postgres, run_async):
    offline.test_failure_has_no_content_and_terminal_state(run_async)


def test_postgres_rejected_and_partial_draft_cannot_complete(postgres, run_async):
    offline.test_rejected_or_partial_success_cannot_be_persisted(run_async)


def test_postgres_request_identity(postgres, run_async):
    offline.test_mismatched_request_rejected(run_async)


def test_postgres_hebrew_27_pages_unicode_roundtrip(postgres, run_async):
    async def run():
        _, _, repo = postgres
        path = Path(__file__).resolve().parents[1] / "docs/examples/roy-alphabet-request.v2.he.json"
        request = StoryRequestV2.model_validate_json(path.read_text(encoding="utf-8"))
        brief = normalize_v2(request, load_profiles_v2(), settings=AppSettings(
            planner_output_tokens=5000, writer_output_tokens=20000, max_input_tokens=64000))
        story = StoryV2.model_validate_json(fixture_steps_v2(brief)[1].response_json)
        result = GenerationSuccessV2(request_id="synthetic", story=story,
            quality=QualityReport(passed=True, check_version="test", rubric_version="test"),
            resolved_constraints=brief.constraints, usage=UsageSummary(), total_latency_seconds=0.1)
        ident = await repo.create(brief)
        await repo.start(ident)
        await repo.complete(ident, brief, result)
        saved = await repo.get(ident)
        assert saved.pages == tuple(page.model_dump(mode="json") for page in story.pages)
        assert [page["page_number"] for page in saved.pages] == list(range(1, 28))
        assert [page["target_id"] for page in saved.pages] == [target.target_id for target in request.structure.targets]
        import json
        assert StoryV2.model_validate_json(json.dumps({**saved.content, "pages": saved.pages},
                                                    ensure_ascii=False)).model_dump_json() == story.model_dump_json()
    run_async(run())


@pytest.mark.parametrize("race", ["start", "complete", "complete_fail"])
def test_postgres_competing_updates_have_exactly_one_winner(postgres, run_async, race):
    async def run():
        _, _, repo = postgres
        brief, result = offline.book()
        ident = await repo.create(brief)
        ready = asyncio.Event()
        async def compete(operation):
            await ready.wait()
            return await operation
        if race == "start":
            operations = [repo.start(ident), repo.start(ident)]
        else:
            await repo.start(ident)
            failure = GenerationFailure(request_id="test", usage=UsageSummary(), total_latency_seconds=0.,
                error=GenerationError(code="QUALITY_REJECTED", stage="quality", retryable=False, message="Rejected"))
            operations = [repo.complete(ident, brief, result), repo.fail(ident, failure) if race == "complete_fail"
                          else repo.complete(ident, brief, result)]
        tasks = [asyncio.create_task(compete(operation)) for operation in operations]
        # Hold the row lock until both independent transactions have attempted work.
        async with postgres[1].begin() as lock_session:
            await lock_session.execute(select(StoryRecord).where(StoryRecord.id == ident).with_for_update())
            ready.set()
            await asyncio.sleep(0.1)
            assert not any(task.done() for task in tasks)
        outcomes = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=15)
        assert sum(value is None for value in outcomes) == 1
        assert sum(isinstance(value, InvalidTransition) for value in outcomes) == 1
        saved = await repo.get(ident)
        if race == "start":
            assert saved.status == "processing" and saved.pages == ()
        elif saved.status == "completed":
            assert len(saved.pages) == 2 and saved.content is not None
        else:
            assert saved.status == "failed" and saved.pages == () and saved.content is None
    run_async(run())


def test_postgres_migration_upgrade_downgrade(postgres, run_async):
    config = Config("alembic.ini")
    command.check(config)
    command.downgrade(config, "base")
    async def absent():
        async with postgres[0].connect() as connection:
            assert await connection.scalar(text("SELECT to_regclass('public.stories')")) is None
            assert await connection.scalar(text("SELECT to_regclass('public.story_pages')")) is None
    run_async(absent())
    command.upgrade(config, "head")
    command.check(config)


def test_postgres_privacy_and_sql_parameter_redaction(postgres, run_async, caplog):
    offline.test_database_logging_and_personal_data_minimization(run_async, caplog)


def test_postgres_read_during_completion_is_consistent(postgres, run_async):
    async def run():
        engine, _, writer = postgres
        brief, result = offline.book()
        ident = await writer.create(brief)
        await writer.start(ident)
        header_read, continue_read = asyncio.Event(), asyncio.Event()
        class PausedPageSession(AsyncSession):
            async def scalars(self, *args, **kwargs):
                header_read.set()
                await continue_read.wait()
                return await super().scalars(*args, **kwargs)
        reader = SqlAlchemyStoryRepository(async_sessionmaker(engine, class_=PausedPageSession))
        reading = asyncio.create_task(reader.get(ident))
        await asyncio.wait_for(header_read.wait(), timeout=5)
        completing = asyncio.create_task(writer.complete(ident, brief, result))
        try:
            await asyncio.sleep(0.1)
            assert not completing.done(), "Completion must wait until the reader finishes its snapshot"
        finally:
            continue_read.set()
            snapshot, _ = await asyncio.wait_for(asyncio.gather(reading, completing), timeout=10)
        assert snapshot.status == "processing" and snapshot.pages == () and snapshot.content is None
        saved = await writer.get(ident)
        assert saved.status == "completed" and len(saved.pages) == 2
    run_async(run())


def test_postgres_combining_marks_and_multilingual_personalization(postgres, run_async):
    async def run():
        _, sessions, repo = postgres
        brief, result = offline.book("he")
        theme = "\u05dc\u05d9\u05dc\u05d4 \U0001f319 caf\u00e9 e\u0301 \u0627\u0644\u0639\u0631\u0628\u064a\u0629"
        brief = brief.model_copy(update={"request": brief.request.model_copy(update={"theme": theme})})
        ident = await repo.create(brief)
        await repo.start(ident)
        await repo.complete(ident, brief, result)
        async with sessions() as session:
            row = await session.get(StoryRecord, ident)
            assert row.theme == theme
            assert row.theme.encode("utf-8") == theme.encode("utf-8")
        assert (await repo.get(ident)).pages == tuple(page.model_dump(mode="json") for page in result.story.pages)
    run_async(run())
