"""Real PostgreSQL canonical persistence. Fake data only; no projector/LLM calls."""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from canonical_helpers import NOW, ai_fixture, manual
from test_persistence_postgresql import postgres
from storyforge.application.books import InternalBookService
from storyforge.domain.book_capacity import AITextCapacityPolicy, BookCapacityPolicy, CapacityExceeded
from storyforge.domain.book_errors import BookConflict, InvalidBook
from storyforge.domain.books import AISourceSnapshot, AssetBinding, AssetReference, BookDetail, ManualBookCreate, PageInput
from storyforge.domain.documents import ImageBlock, Layout, PageDocument, TextBlock
from storyforge.domain.generation import GenerationFailure, GenerationError, QualityIssue, QualityReport, UsageSummary
from storyforge.persistence.book_models import BookPageRecord, BookRecord
from storyforge.persistence.models import StoryPageRecord, StoryRecord
from storyforge.persistence.unit_of_work import SqlAlchemyBookUnitOfWork

pytestmark=[pytest.mark.postgresql,pytest.mark.enable_socket,pytest.mark.allow_hosts(["127.0.0.1","::1"])]


def service(sessions,**kwargs):
    return InternalBookService(lambda:SqlAlchemyBookUnitOfWork(sessions,**kwargs),clock=lambda:NOW)


async def pending_source(stories):
    brief,result,projection=ai_fixture()
    ident=await stories.create(brief)
    await stories.start(ident)
    raw=projection.model_dump(mode="json")
    # Replace only the trusted backend context's source identifier, not AI content.
    raw["origin"]["generation_id"]=str(ident)
    import json
    return brief,result,BookDetail.model_validate_json(json.dumps(raw))


@pytest.mark.parametrize("language",["he","en"])
def test_manual_create_retrieve_title_update_and_separate_session(postgres,run_async,language):
    async def run():
        _,sessions,_=postgres
        books=service(sessions)
        created=await books.create_manual(manual(language=language))
        assert await books.get(created.book_id)==created
        assert [p.position for p in created.pages]==[1,2]
        assert (await books.update_title(created.book_id,1,"\u05e1\u05e4\u05e8 \U0001f319")).revision==2
        assert (await service(sessions).get(created.book_id)).title=="\u05e1\u05e4\u05e8 \U0001f319"
        assert await books.get(uuid4()) is None
        with pytest.raises(BookConflict):await books.update_title(created.book_id,1,"stale")
    run_async(run())


def test_empty_manual_draft_and_atomic_invalid_inputs(postgres,run_async):
    async def run():
        _,sessions,_=postgres
        books=service(sessions)
        saved=await books.create_manual(manual(pages=0))
        assert saved.page_count==0 and (await books.get(saved.book_id)).pages==()
        bad=manual().model_copy(update={"title":"\u202eprivate"})
        with pytest.raises(InvalidBook) as error:await books.create_manual(bad)
        assert "private" not in str(error.value)
        async with sessions() as session:
            assert len((await session.scalars(select(BookRecord))).all())==1
    run_async(run())


def test_real_27_page_agent1_projection_and_initial_snapshot(postgres,run_async):
    async def run():
        _,sessions,stories=postgres
        brief,result,projection=await pending_source(stories)
        books=service(sessions)
        assert await books.save_accepted_ai_projection(projection,brief,result)==projection
        saved=await books.get(projection.book_id)
        assert saved==projection and len(saved.pages)==27 and saved.direction=="rtl"
        assert [p.source_target_id for p in saved.pages]==list(brief.constraints.target_ids)
        assert (await stories.get(projection.origin.generation_id)).status=="completed"
        async with sessions() as session:
            row=await session.get(BookRecord,projection.book_id)
            snapshot=AISourceSnapshot.model_validate_json(__import__('json').dumps(row.source_snapshot))
            assert snapshot.resolved_constraints==result.resolved_constraints
        await books.update_title(projection.book_id,1,"Edited private Book")
        # Editing never rewrites the accepted source or its original quality metadata.
        assert (await stories.get(projection.origin.generation_id)).content["title"]==result.story.title
    run_async(run())


@pytest.mark.parametrize("kind",["rejected","partial","projection_mismatch","failed"])
def test_no_failed_or_mismatched_projection_commits_source_or_book(postgres,run_async,kind):
    async def run():
        _,sessions,stories=postgres
        brief,result,projection=await pending_source(stories)
        if kind=="rejected":
            result=result.model_copy(update={"quality":QualityReport(passed=False,
                issues=(QualityIssue(code="unsafe",severity="terminal",guidance="Rejected"),),
                check_version="test",rubric_version="test")})
        elif kind=="partial":result=result.model_copy(update={"story":result.story.model_copy(update={"pages":result.story.pages[:-1]})})
        elif kind=="failed":result=GenerationFailure(request_id="failed",usage=UsageSummary(),total_latency_seconds=0.,
            error=GenerationError(code="QUALITY_REJECTED",stage="quality",retryable=False,message="private-canary"))
        else:projection=projection.model_copy(update={"title":"Other source"})
        with pytest.raises((InvalidBook,ValueError)):
            await service(sessions).save_accepted_ai_projection(projection,brief,result)
        saved=await stories.get(projection.origin.generation_id)
        assert saved.status=="processing" and saved.content is None and saved.pages==()
        assert await service(sessions).get(projection.book_id) is None
    run_async(run())


def test_source_completion_rolls_back_after_late_book_page_failure(postgres,run_async):
    async def run():
        engine,sessions,stories=postgres
        brief,result,projection=await pending_source(stories)
        # Unrelated manual page reserves a canonical UUID; force the insert failure
        # only after source completion and Book header have been staged.
        other=await service(sessions).create_manual(manual(pages=1))
        awaitable=projection.model_copy(update={"pages":(
            projection.pages[0].model_copy(update={"page_id":other.pages[0].page_id}),)+projection.pages[1:]})
        with pytest.raises(IntegrityError):
            await service(sessions).save_accepted_ai_projection(awaitable,brief,result)
        saved=await stories.get(projection.origin.generation_id)
        assert saved.status=="processing" and saved.pages==() and saved.generation_metadata is None
        assert await service(sessions).get(projection.book_id) is None
        assert await service(sessions).get(other.book_id)==other
    run_async(run())


def test_capacity_rejection_rolls_back_and_general_policy_is_configurable(postgres,run_async):
    async def run():
        _,sessions,stories=postgres
        brief,result,projection=await pending_source(stories)
        with pytest.raises(CapacityExceeded):
            await service(sessions,ai_policy=AITextCapacityPolicy(maximum_pages=26)).save_accepted_ai_projection(projection,brief,result)
        assert (await stories.get(projection.origin.generation_id)).status=="processing"
        assert await service(sessions).get(projection.book_id) is None
        await service(sessions,policy=BookCapacityPolicy(maximum_pages=64)).create_manual(manual(pages=33))
        with pytest.raises(CapacityExceeded):await service(sessions).create_manual(manual(pages=33))
    run_async(run())


def test_manual_documents_are_not_limited_by_ai_text_capacity(postgres,run_async):
    async def run():
        _,sessions,_=postgres
        page=PageInput(document=PageDocument(blocks=(TextBlock(block_id="body",language="en",direction="ltr",
            sentence_units=("x"*401,)*129),)))
        strict_ai=service(sessions,ai_policy=AITextCapacityPolicy(maximum_sentence_units=1,maximum_unit_code_points=1))
        created=await strict_ai.create_manual(ManualBookCreate(title="Long manual page",language="en",pages=(page,)))
        saved=await strict_ai.get(created.book_id)
        assert saved.pages[0].document==page.document
        assert len(saved.pages[0].document.blocks[0].sentence_units)==129
    run_async(run())


def test_illustrated_document_and_ready_asset_reference(postgres,run_async):
    async def run():
        _,sessions,_=postgres
        ident=uuid4()
        asset=AssetReference(asset_id=ident,storage_backend="local",object_key=f"objects/{ident}.png",
            checksum="0"*64,media_type="image/png",byte_size=4,width=1,height=1)
        async with SqlAlchemyBookUnitOfWork(sessions) as unit:await unit.books.register_asset(asset)
        page=PageInput(document=PageDocument(layout=Layout(preset="text-image-v1"),blocks=(
            ImageBlock(block_id="picture",slot_key="hero"),)),asset_bindings=(AssetBinding(slot_key="hero",asset_id=ident),))
        created=await service(sessions).create_manual(ManualBookCreate(title="Image draft",language="en",pages=(page,)))
        assert (await service(sessions).get(created.book_id)).pages[0].document==page.document
        assert "object_key" not in created.model_dump_json()
        invalid=page.model_copy(update={"asset_bindings":(AssetBinding(slot_key="hero",asset_id=uuid4()),)})
        with pytest.raises(InvalidBook):await service(sessions).create_manual(ManualBookCreate(title="Missing asset",language="en",pages=(invalid,)))
    run_async(run())


def test_title_update_concurrency_one_winner(postgres,run_async):
    async def run():
        _,sessions,_=postgres
        books=service(sessions)
        created=await books.create_manual(manual())
        async with sessions.begin() as lock:
            await lock.execute(select(BookRecord).where(BookRecord.id==created.book_id).with_for_update())
            tasks=[asyncio.create_task(books.update_title(created.book_id,1,title)) for title in ("One","Two")]
            await asyncio.sleep(.1)
            assert not any(t.done() for t in tasks)
        outcomes=await asyncio.wait_for(asyncio.gather(*tasks,return_exceptions=True),timeout=10)
        assert sum(isinstance(v,BookDetail) for v in outcomes)==1
        assert sum(isinstance(v,BookConflict) for v in outcomes)==1
        assert (await books.get(created.book_id)).revision==2
    run_async(run())


def test_real_sql_constraints_deferred_order_and_immutable_origin(postgres,run_async):
    async def run():
        _,sessions,_=postgres
        book=await service(sessions).create_manual(manual())
        for values in ({"revision":0},{"creation_mode":"TEMPLATE_BASED"},{"direction":"rtl"},{"title":"x"*121}):
            with pytest.raises(DBAPIError):
                async with sessions.begin() as session:await session.execute(update(BookRecord).where(BookRecord.id==book.book_id).values(**values))
        with pytest.raises(IntegrityError):
            async with sessions.begin() as session:
                await session.execute(update(BookPageRecord).where(BookPageRecord.id==book.pages[0].page_id).values(position=3))
        async with sessions.begin() as session:
            await session.execute(text("SET CONSTRAINTS uq_book_page_position DEFERRED"))
            await session.execute(update(BookPageRecord).where(BookPageRecord.id==book.pages[0].page_id).values(position=2))
            await session.execute(update(BookPageRecord).where(BookPageRecord.id==book.pages[1].page_id).values(position=1))
            await session.execute(update(BookRecord).where(BookRecord.id==book.book_id).values(revision=2))
        saved=await service(sessions).get(book.book_id)
        assert [p.page_id for p in saved.pages]==[book.pages[1].page_id,book.pages[0].page_id]
        async with sessions.begin() as session:
            await session.execute(update(BookRecord).where(BookRecord.id==book.book_id).values(
                state="finalized",revision=3,finalized_at=NOW))
        with pytest.raises(BookConflict):await service(sessions).update_title(book.book_id,3,"Cannot edit")
        with pytest.raises(IntegrityError):
            async with sessions.begin() as session:
                await session.execute(update(BookPageRecord).where(BookPageRecord.id==book.pages[0].page_id).values(document={"invalid":True}))
    run_async(run())


def test_origin_snapshot_and_initial_identity_are_database_immutable(postgres, run_async):
    async def run():
        _,sessions,stories=postgres
        brief,result,projection=await pending_source(stories)
        books=service(sessions)
        await books.save_accepted_ai_projection(projection,brief,result)
        forbidden={
            "source_story_id":uuid4(),"source_snapshot":{},"created_at":NOW-timedelta(seconds=1),
            "schema_version":"2","creation_mode":"MANUAL","id":uuid4(),
            "language":"en" if projection.language=="he" else "he",
        }
        for field,value in forbidden.items():
            with pytest.raises(DBAPIError,match="BOOK_ORIGIN_IMMUTABLE"):
                async with sessions.begin() as session:
                    await session.execute(update(BookRecord).where(BookRecord.id==projection.book_id).values(revision=2,**{field:value}))
        edited=await books.update_title(projection.book_id,1,"Edited title")
        assert edited.revision==2 and edited.origin==projection.origin
        async with sessions() as session:
            row=await session.get(BookRecord,projection.book_id)
            assert row.source_story_id==projection.origin.generation_id
            assert AISourceSnapshot.model_validate_json(__import__('json').dumps(row.source_snapshot)).resolved_constraints==result.resolved_constraints
    run_async(run())


def test_migration_rollback_preserves_0001_source_data(postgres,run_async):
    _,sessions,stories=postgres
    async def source():
        brief,_,_=ai_fixture()
        return await stories.create(brief)
    ident=run_async(source())
    command.check(Config("alembic.ini"))
    command.downgrade(Config("alembic.ini"),"0001")
    async def preserved():
        async with sessions() as session:
            assert await session.get(StoryRecord,ident) is not None
            assert await session.scalar(text("SELECT to_regclass('public.books')")) is None
    run_async(preserved())
    command.upgrade(Config("alembic.ini"),"head")
    command.check(Config("alembic.ini"))


def test_uow_cancellation_rollback_and_closed_scope(postgres,run_async):
    async def run():
        _,sessions,_=postgres
        from canonical_helpers import manual_detail
        book=manual_detail()
        unit=SqlAlchemyBookUnitOfWork(sessions)
        with pytest.raises(asyncio.CancelledError):
            async with unit:
                await unit.books.add(book)
                raise asyncio.CancelledError()
        assert await service(sessions).get(book.book_id) is None
        with pytest.raises(RuntimeError):await unit.books.get(book.book_id)
    run_async(run())


def test_one_initial_book_per_source_and_source_immutability(postgres,run_async):
    async def run():
        _,sessions,stories=postgres
        brief,result,projection=await pending_source(stories)
        books=service(sessions)
        await books.save_accepted_ai_projection(projection,brief,result)
        async with sessions() as session:
            row=await session.get(BookRecord,projection.book_id)
            snapshot=AISourceSnapshot.model_validate_json(__import__('json').dumps(row.source_snapshot))
        duplicate=projection.model_copy(update={"book_id":uuid4(),"pages":tuple(
            page.model_copy(update={"page_id":uuid4()}) for page in projection.pages)})
        with pytest.raises(IntegrityError):
            async with SqlAlchemyBookUnitOfWork(sessions) as unit:await unit.books.add(duplicate,snapshot)
        for statement in (
            update(StoryRecord).where(StoryRecord.id==projection.origin.generation_id).values(theme="changed"),
            update(StoryPageRecord).where(StoryPageRecord.story_id==projection.origin.generation_id).values(sentence_units=["changed"]),
        ):
            with pytest.raises(IntegrityError):
                async with sessions.begin() as session:await session.execute(statement)
        assert await books.get(projection.book_id)==projection
    run_async(run())


def test_failed_stored_source_and_reserved_template_mode_cannot_create_books(postgres,run_async):
    async def run():
        _,sessions,stories=postgres
        brief,result,projection=await pending_source(stories)
        await stories.fail(projection.origin.generation_id,GenerationFailure(request_id="test",usage=UsageSummary(),
            total_latency_seconds=0.,error=GenerationError(code="QUALITY_REJECTED",stage="quality",retryable=False,message="Rejected")))
        snapshot=AISourceSnapshot(profile_id=result.story.profile_id,profile_version=result.story.profile_version,
            policy_version=brief.constraints.policy_version,quality_check_version=result.quality.check_version,
            rubric_version=result.quality.rubric_version,resolved_constraints=brief.constraints)
        with pytest.raises(InvalidBook):
            async with SqlAlchemyBookUnitOfWork(sessions) as unit:await unit.books.add(projection,snapshot)
        assert await service(sessions).get(projection.book_id) is None
        from storyforge.domain.books import BookOrigin
        from canonical_helpers import manual_detail
        template=manual_detail().model_copy(update={"creation_mode":"TEMPLATE_BASED",
            "origin":BookOrigin(template_version_id=uuid4(),page_variant_id="standard")})
        with pytest.raises(InvalidBook):
            async with SqlAlchemyBookUnitOfWork(sessions) as unit:await unit.books.add(template)
    run_async(run())


def test_shared_read_lock_preserves_book_snapshot(postgres,run_async):
    async def run():
        engine,sessions,_=postgres
        from sqlalchemy.ext.asyncio import AsyncSession,async_sessionmaker
        book=await service(sessions).create_manual(manual())
        header_read,resume=asyncio.Event(),asyncio.Event()
        class PausedSession(AsyncSession):
            async def scalars(self,*args,**kwargs):
                header_read.set()
                await resume.wait()
                return await super().scalars(*args,**kwargs)
        reader=service(async_sessionmaker(engine,class_=PausedSession,expire_on_commit=False))
        reading=asyncio.create_task(reader.get(book.book_id))
        await asyncio.wait_for(header_read.wait(),timeout=5)
        writing=asyncio.create_task(service(sessions).update_title(book.book_id,1,"New title"))
        try:
            await asyncio.sleep(.1)
            assert not writing.done()
        finally:
            resume.set()
            old,new=await asyncio.wait_for(asyncio.gather(reading,writing),timeout=10)
        assert old==book and new.revision==2 and new.title=="New title"
    run_async(run())


def test_privacy_and_invalid_internal_boundaries(postgres,run_async,caplog,capsys):
    async def run():
        engine,sessions,_=postgres
        assert engine.echo is False and engine.sync_engine.hide_parameters is True
        books=service(sessions)
        command=manual().model_copy(update={"title":"private-book-canary"})
        saved=await books.create_manual(command)
        assert "object_key" not in saved.model_dump_json()
        with pytest.raises(InvalidBook):await books.get("not-a-uuid")
        with pytest.raises(InvalidBook):await books.update_title(saved.book_id,True,"changed")
        with pytest.raises(InvalidBook) as error:await books.create_manual(command.model_copy(update={"title":"\u202eprivate-canary"}))
        assert "canary" not in str(error.value)
        assert "private-book-canary" not in caplog.text
        assert engine.url.password not in caplog.text
    run_async(run())
    output=capsys.readouterr()
    assert "private-book-canary" not in output.out+output.err
