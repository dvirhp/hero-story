# Persistence foundation handoff

## Scope, branch and baseline

Authorized initial persistence foundation only. Existing documents describe persistence as out of scope for the original engine milestones; this work is separately authorized. Nothing enables persistence automatically, changes HTTP contracts, or stores LangGraph state. No AI calls, queue, authentication, billing changes, push or deployment.

Branch: `feature/storyforge-persistence-foundation`.
Baseline: `5ae24e9` (existing v2 contracts). Worktree: `C:/Users/dvir3/storyforge-persistence`.
Implementation commit: `b26626b5cfcff33691004197bebdc97a4856a330`. The following documentation-only commit records this identifier; use `git log -1 --format=%H` for the branch tip. Other agents' uncommitted provider/diagnostics changes were deliberately excluded.

## Architecture and decisions

SQLAlchemy async engine/session factory, asyncpg PostgreSQL driver and Alembic. Inject the session factory into `SqlAlchemyStoryRepository`; no global connections or implicit environment reads in application modules. Dispose the returned engine during application shutdown. Each repository mutation owns a fresh session and transaction; completion status, metadata and all pages commit together. Conditional UPDATE guards serialize competing lifecycle transitions; invalid transitions raise a fixed `InvalidTransition` without child data. Reads use a transaction, explicit page-number ordering and a PostgreSQL shared story-row lock until all pages are loaded. The shared lock prevents READ COMMITTED snapshots from mixing an old status/header with newly committed pages.

`StoryRepository` is the structural protocol; `SqlAlchemyStoryRepository` implements it. Async interfaces:

- `create(brief: NormalizedBriefV2) -> UUID`: pending record with minimal request metadata.
- `start(story_id: UUID) -> None`: pending to processing only.
- `complete(story_id, brief, result: GenerationSuccessV2) -> None`: processing to completed only. Revalidates typed inputs, passing quality, contextual story constraints and original request identity. Saves accepted content only.
- `fail(story_id, result: GenerationFailure) -> None`: processing to failed only. Saves error code and safe usage, never an error message or draft.
- `get(story_id) -> SavedStory | None`: detached typed snapshot with header content, ordered page dictionaries and safe generation metadata.

No implicit retry, resume, idempotency key, background worker or workflow interception. Explicit transition errors let future callers decide retry semantics. UUIDs identify stories, not users. No owner column or invented identities: add a real ownership FK in a later authenticated migration.

## Tables and constraints

`stories`: UUID primary key; database-generated timezone-aware creation timestamp; indexed lifecycle status; child display name; strict domain age in months; language; user-selected page count; story type; theme; allowlisted structured request options (`text_density`, ordered `structure`, requested title); API schema version; page policy version; accepted story header JSON (title, language, direction, profile ID/version, page count/schema); safe generation metadata JSON; failure code.

Checks: nonnegative age, positive count, supported language/type/status; content must be SQL NULL unless completed and must exist when completed. No hardcoded maximum count: existing configurable PagePolicy admission owns the initial 1-32 limit; age never determines it.

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

Verification on Python 3.12.16: **758 passed** in 72.91 seconds for the complete offline suite; **8 persistence cases passed** in 2.30 seconds on the focused run. Wheel and source-distribution builds passed (`uv build`); Compose configuration validation and `git diff --check` passed. Those initial results were SQLite/offline only. The Docker blocker was resolved in the follow-up below; real PostgreSQL runtime results supersede that limitation.

## Privacy, limitations and future work

Stores the explicitly required child name, age, theme and accepted story content, which are sensitive. Omits birth dates, user identities, freeform guidance, interests, pronouns, prompts, drafts, raw failures/diagnostics and secrets. Request metadata is deliberately a minimized subset, not a full replayable original request. Structured educational targets may themselves contain personalization; treat all JSON/content as private. SQL echo is disabled and parameters hidden; callers must not log exceptions, DSNs or returned content. Database access, TLS, encryption, backups, deletion/retention policy and authorization are deployment responsibilities not implemented here. No public read endpoint exists. Product approval of retention and ownership is required before enabling storage for actual child data.

No automatic failed/pending recovery after process crashes; processing may remain until a future explicit recovery policy. No completed_at, pagination, deletion service, row-level security, audit history or search. JSON provides versioned flexibility without provider SDK coupling; later typed sub-tables can migrate it if query needs emerge. Policy/schema/profile/prompt/rubric/pricing versions remain explicit; full profile snapshots are not saved. `SavedStory` is a detached frozen dataclass with mutable JSON copies, not an HTTP schema. IDs and content consistency cannot replace authentication.

## Proposed v2/frontend integration (requires separate endpoint approval)

At application composition, construct database resources only when persistence is explicitly configured; run Alembic outside API startup. After existing v2 validation/admission resolves a brief, call create/start, then invoke the unchanged bounded public engine. Pass the original normalized brief and only `GenerationSuccessV2` to complete; pass sanitized `GenerationFailure` to fail. Do not connect a provider, graph checkpointer, callback or draft to this repository. Resolve cancellation/database failure behavior, request idempotency and response-to-story-ID mapping before changing endpoints. Database errors must not cause a generation retry or expose sensitive SQL. An HTTP success with failed persistence needs an explicit product policy.

Future saved-story routes require real ownership/authentication, access control, a typed response DTO, deterministic pagination and retention/deletion decisions. Frontend can eventually use returned persistent story UUIDs and ordered sentence units; current generate responses and frontend contracts remain unchanged. Do not expose child metadata through unauthenticated list/read endpoints.


## Runtime verification follow-up (2026-11-05)

Docker initially returned `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.` `docker desktop status` reported that Desktop was not running. `docker desktop start` succeeded. Docker engine **28.5.1** became available; Compose pulled `postgres:17` and started a healthy isolated container on `127.0.0.1:5433`. Runtime server: **PostgreSQL 17.11 (Debian 17.11-1.pgdg13+2)**. The local `storyforge` database was migrated to **0001 (head)** and `alembic check` reported no new upgrade operations. No production database or AI service was contacted.

New file: `tests/test_persistence_postgresql.py`, marked `postgresql`. These are real PostgreSQL/asyncpg connections and transactions, with Alembic-created tables; no database operation is mocked or replaced by SQLite. Story content comes from existing offline synthetic fixtures, not an LLM. Shared contract tests reuse assertions from `test_persistence.py` with a real PostgreSQL session factory. The distinct SQLite tests still use in-memory aiosqlite; offline SQL compilation alone is not a runtime test.

Each PostgreSQL test creates a uniquely named `storyforge_test_<uuid>` database using the local development role, migrates it, then drops only that generated database in cleanup. The supplied database is never downgraded or dropped. The migration round trip operates on a disposable database only. Local test role requires CREATE DATABASE permission; this is appropriate only for local testing. URL must explicitly use `postgresql+asyncpg` at `127.0.0.1`; sockets are enabled only for these marked tests, with loopback connect restrictions. If the opt-in URL is absent, tests explicitly skip with no SQLite fallback. A configured but unavailable database fails tests rather than silently skipping. A killed test process may leave a generated test database requiring deliberate local cleanup.

Coverage:

- Create/retrieve for both current languages, persisted UUID/timestamp, accepted page content.
- Full 27-page Hebrew alphabet fixture round trip, contiguous page order and educational target order, exact sentence-unit equality and reconstruction from stored JSON.
- Hebrew/English plus emoji, accented Latin, combining marks and Arabic in personalization round trips without Unicode normalization or reversal. This verifies storage, not support for generating additional languages.
- Atomic completion and rollback on a real duplicate-page-number violation after the status update; no partial accepted header/metadata remains. SQL status, language, age, count and FK constraints are exercised.
- Invalid/missing/terminal lifecycle transitions and request mismatch. A failed result, rejected quality result and incomplete story cannot be passed as completed, including attempts constructed with model_copy that bypasses initial validation. Failed records keep no draft/pages/error message.
- Two competing starts, two competing completions and completion versus failure. An explicitly held PostgreSQL row lock ensures overlapping transactions; exactly one wins and the other receives InvalidTransition. Winner content/pages remain consistent.
- Paused read between header and page queries while completion runs. Reader retains processing with no pages; completion waits for the reader, then subsequent reads see the entire completed story. This motivated the shared row-lock correction in repository.get.
- Real upgrade, drift check, downgrade to base with table absence checks, re-upgrade and drift check.
- Privacy canaries: omitted guidance/interests; SQL echo disabled; SQL parameters hidden in constraint-exception formatting; no canaries or URL password in captured application logs; engine URL string masks password.

Reproduction from repository root in PowerShell (the documented password is disposable local configuration only):

```powershell
docker desktop start
docker info --format '{{.ServerVersion}}'
docker compose -f compose.persistence.yaml up -d --wait
$env:STORYFORGE_DATABASE_URL = 'postgresql+asyncpg://storyforge_local:local-development-only@127.0.0.1:5433/storyforge'
$env:STORYFORGE_TEST_POSTGRES_URL = $env:STORYFORGE_DATABASE_URL
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m alembic current
.venv/Scripts/python.exe -m alembic check
.venv/Scripts/python.exe -m pytest tests/test_persistence_postgresql.py -q
.venv/Scripts/python.exe -m pytest -q
# To run strictly offline/SQLite tests separately:
Remove-Item Env:STORYFORGE_TEST_POSTGRES_URL
.venv/Scripts/python.exe -m pytest -m 'not postgresql' -q
```

Final results on Python 3.12.16:

- **14 real PostgreSQL integration cases passed** in 7.84 seconds (focused final PostgreSQL run).
- **773 total regression cases passed** in 52.91 seconds after all implementation/test changes: 14 PostgreSQL cases plus 759 existing/offline/SQLite cases. No skipped PostgreSQL tests in this configured run; no live AI calls.
- Nine cases in `tests/test_persistence.py` use SQLite or offline DDL compilation. They are not counted as PostgreSQL runtime evidence. The remainder of the non-PostgreSQL suite includes existing mocked-provider contract tests.
- Real database migration upgrade/current/check passed; migration round-trip test downgraded and re-upgraded only its disposable database. No migration revision beyond 0001.
- Wheel/source-distribution builds and `git diff --check` passed.
- After test cleanup, zero `storyforge_test_*` databases remained. The Compose development database remained at revision 0001 with zero story records. Container is left running and healthy for review; stop it with `docker compose -f compose.persistence.yaml stop` when finished. The named volume persists.

The first runtime test run had a test-only AsyncEngine attribute lookup error; correcting it to inspect sync_engine.hide_parameters resolved the failure. No PostgreSQL test failures remain.

Remaining limits: these concurrency cases prove the exercised transaction schedules on local PostgreSQL's default READ COMMITTED isolation, not every distributed failure, sustained load, failover or arbitrary direct SQL update. Shared read locks may delay writers for the duration of a read transaction; callers must keep transactions short and configure production timeout/deadlock handling. The repository performs its own bounded transactions and has no retry policy. Cross-row count/quality invariants still depend on the trusted repository and genuine engine-approved success envelope; arbitrary database writers or forged passing quality flags cannot be prevented by these checks. The repository does not rerun or cryptographically attest the quality gate. No direct raw SQL writes should be exposed to API clients.

Privacy review: all fixtures are synthetic. Stored child name/age/theme and accepted content remain sensitive. Metadata minimization and parameter masking are verified, but do not establish complete system-wide privacy. SQL/server/driver errors can contain details; never log arbitrary exception objects, DSNs, returned story content or validation inputs. Captured application logs are not evidence about future deployment collectors or PostgreSQL administrator settings. Production credentials must come from approved secret configuration, not this Compose password. TLS, encryption, retention/deletion, ownership, authorization and backup access remain prerequisites before any real-child-data integration. No existing API, LangGraph, adapter or frontend files were changed.

Follow-up modified files: `src/storyforge/persistence/repository.py`, `tests/test_persistence.py`, `pyproject.toml` (marker registration), this handoff; created `tests/test_persistence_postgresql.py`. No schema change or new migration revision was needed. Future v2 integration requirements above remain unchanged; configure read/statement/lock timeouts and handle persistence errors without generation retries or private error exposure.
