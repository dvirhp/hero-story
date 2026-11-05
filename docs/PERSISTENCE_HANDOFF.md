# Persistence foundation handoff

## Scope, branch and baseline

Authorized initial persistence foundation only. Existing documents describe persistence as out of scope for the original engine milestones; this work is separately authorized. Nothing enables persistence automatically, changes HTTP contracts, or stores LangGraph state. No AI calls, queue, authentication, billing changes, push or deployment.

Branch: `feature/storyforge-persistence-foundation`.
Baseline: `5ae24e9` (existing v2 contracts). Worktree: `C:/Users/dvir3/storyforge-persistence`.
Implementation commit: use `git log -1 --format=%H` on this branch; the handoff is included in that commit. Other agents' uncommitted provider/diagnostics changes were deliberately excluded.

## Architecture and decisions

SQLAlchemy async engine/session factory, asyncpg PostgreSQL driver and Alembic. Inject the session factory into `SqlAlchemyStoryRepository`; no global connections or implicit environment reads in application modules. Dispose the returned engine during application shutdown. Each repository mutation owns a fresh session and transaction; completion status, metadata and all pages commit together. Conditional UPDATE guards serialize competing lifecycle transitions; invalid transitions raise a fixed `InvalidTransition` without child data. Reads use a transaction and explicit page-number ordering.

`StoryRepository` is the structural protocol; `SqlAlchemyStoryRepository` implements it. Async interfaces:

- `create(brief: NormalizedBriefV2) -> UUID`: pending record with minimal request metadata.
- `start(story_id: UUID) -> None`: pending to processing only.
- `complete(story_id, brief, result: GenerationSuccessV2) -> None`: processing to completed only. Revalidates typed inputs, passing quality, contextual story constraints and original request identity. Saves accepted content only.
- `fail(story_id, result: GenerationFailure) -> None`: processing to failed only. Saves error code and safe usage, never an error message or draft.
- `get(story_id) -> SavedStory | None`: detached typed snapshot with header content, ordered page dictionaries and safe generation metadata.

No implicit retry, resume, idempotency key, background worker or workflow interception. Explicit transition errors let future callers decide retry semantics. UUIDs identify stories, not users. No owner column or invented identities: add a real ownership FK in a later authenticated migration.

## Tables and constraints

`stories`: UUID primary key; database-generated timezone-aware creation timestamp; indexed lifecycle status; child display name; strict domain age in months; language; user-selected page count; story type; theme; allowlisted structured request options (`text_density`, ordered `structure`, requested title); API schema version; page policy version; accepted story header JSON (title, language, direction, profile ID/version, page count/schema); safe generation metadata JSON; failure code.

Checks: nonnegative age, positive count, supported language/type/status; content must be SQL NULL unless completed and must exist when completed. No hardcoded maximum count: existing configurable PagePolicy admission owns the initial 1?32 limit; age never determines it.

`story_pages`: composite primary key `(story_id, page_number)`; cascading story FK; positive page number; unique `(story_id, page_id)`; optional ordered target ID and JSON sentence units. Text derives from sentence units; no duplicated generated prose. Retrieval always orders by page_number. Exact count, contiguous numbering, target order, density and quality are enforced by domain/repository validation. SQL alone does not certify those cross-row invariants; direct SQL writes must be restricted.

Safe metadata allowlist includes per-attempt provider/model, stage, prompt/pricing versions, latency, token usage/source, cost/reservation, outcome, aggregate unknown flags, known cost subtotal/upper estimate, total duration and successful quality/rubric versions. Unknown stays null/unknown rather than zero. Cost estimates remain estimates. Separate planner/writer models are preserved.

## Files

Created: `src/storyforge/persistence/__init__.py`, `database.py`, `models.py`, `repository.py`; `alembic.ini`; `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/0001_initial_story_persistence.py`; `compose.persistence.yaml`; `tests/test_persistence.py`; this handoff.
Modified: `pyproject.toml`, `uv.lock` (SQLAlchemy async, Alembic, asyncpg; dev-only aiosqlite and locked transitive packages). No shared API, domain, adapter, orchestration or frontend modifications.

## Local setup and migrations

Python 3.12+; sync the committed lock with `uv sync --locked`. Docker Desktop must be running for PostgreSQL. From repository root in PowerShell:

```powershell
docker compose -f compose.persistence.yaml up -d --wait
$env:STORYFORGE_DATABASE_URL = 'postgresql+asyncpg://storyforge_local:local-development-only@127.0.0.1:5433/storyforge'
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m alembic current
.venv/Scripts/python.exe -m alembic check
```

Compose binds localhost port 5433 and a named volume; its publicly documented password is exclusively a disposable local-development value. It is not a production credential. Do not reuse it outside this setup. No application dotenv/config file is changed.

Revision `0001`, parent `None`, creates both tables/index/constraints. Migration files contain explicit DDL and do not import current models. `env.py` imports metadata for future autogeneration. Offline PostgreSQL SQL: `.venv/Scripts/python.exe -m alembic upgrade head --sql` (no database or credentials required).

Rollback (destructive: both tables and their story data are dropped; back up data first): `.venv/Scripts/python.exe -m alembic downgrade base`. Reapply using `upgrade head`. Stop local service with `docker compose -f compose.persistence.yaml down`; volume remains. Do not remove the named volume unless intentionally discarding local data.

## Verification

Offline suite: `.venv/Scripts/python.exe -m pytest tests/test_persistence.py -q`. SQLite/aiosqlite uses real transactions and enabled FK checks. Tests cover Hebrew/English accepted books, ordered pages, timestamps, lifecycle transitions, failures without content/error text, request mismatch, constraints, FK rejection, atomic rollback after a page-insert failure, rejected/partial output rejection, upgrade/check/downgrade/re-upgrade and PostgreSQL offline DDL compilation. Uses existing synthetic fixtures only, no network or AI keys. Windows tests reuse the preconstructed event loop from conftest, preserving the socket guard; migration test adapts asyncio.run to that same loop.

Verification on Python 3.12.16: **758 passed** in 72.91 seconds for the complete offline suite; **8 persistence cases passed** in 2.30 seconds on the focused run. Wheel and source-distribution builds passed (`uv build`); Compose configuration validation and `git diff --check` passed. PostgreSQL runtime integration is not claimed: Docker client exists but Docker Desktop Linux engine is unavailable on this host. PostgreSQL DDL compilation is covered; run migrations/check and a repository smoke test against local PostgreSQL before integration/release.

## Privacy, limitations and future work

Stores the explicitly required child name, age, theme and accepted story content, which are sensitive. Omits birth dates, user identities, freeform guidance, interests, pronouns, prompts, drafts, raw failures/diagnostics and secrets. Request metadata is deliberately a minimized subset, not a full replayable original request. Structured educational targets may themselves contain personalization; treat all JSON/content as private. SQL echo is disabled and parameters hidden; callers must not log exceptions, DSNs or returned content. Database access, TLS, encryption, backups, deletion/retention policy and authorization are deployment responsibilities not implemented here. No public read endpoint exists. Product approval of retention and ownership is required before enabling storage for actual child data.

No automatic failed/pending recovery after process crashes; processing may remain until a future explicit recovery policy. No completed_at, pagination, deletion service, row-level security, audit history or search. JSON provides versioned flexibility without provider SDK coupling; later typed sub-tables can migrate it if query needs emerge. Policy/schema/profile/prompt/rubric/pricing versions remain explicit; full profile snapshots are not saved. `SavedStory` is a detached frozen dataclass with mutable JSON copies, not an HTTP schema. IDs and content consistency cannot replace authentication.

## Proposed v2/frontend integration (requires separate endpoint approval)

At application composition, construct database resources only when persistence is explicitly configured; run Alembic outside API startup. After existing v2 validation/admission resolves a brief, call create/start, then invoke the unchanged bounded public engine. Pass the original normalized brief and only `GenerationSuccessV2` to complete; pass sanitized `GenerationFailure` to fail. Do not connect a provider, graph checkpointer, callback or draft to this repository. Resolve cancellation/database failure behavior, request idempotency and response-to-story-ID mapping before changing endpoints. Database errors must not cause a generation retry or expose sensitive SQL. An HTTP success with failed persistence needs an explicit product policy.

Future saved-story routes require real ownership/authentication, access control, a typed response DTO, deterministic pagination and retention/deletion decisions. Frontend can eventually use returned persistent story UUIDs and ordered sentence units; current generate responses and frontend contracts remain unchanged. Do not expose child metadata through unauthenticated list/read endpoints.
