# Persistence foundation handoff

> **Latest task: anonymous access / daily-capability-limit design revision (2026-11-05).** Phase A is accepted in principle, but **Phase B is not authorized**. See [ARCHITECTURE.md](ARCHITECTURE.md), [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md), [API_CONTRACTS.md](API_CONTRACTS.md) and the revision delta below. Anonymous story/image generation and account-free template preview are now required; secure anonymous ownership replaces the earlier account-required/private-local-only product target. No session, quota, image, product or new API code/schema exists. Historical implementation/test evidence remains valid only for the accepted persistence foundation. Earlier integration plans/security decisions below are historical where superseded; the v2 save=true proposal remains unimplemented and superseded by v3.

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

Runtime verification/read-consistency implementation commit: `6cc8ef947ed671b097e546c462cae8c924ec15ed` on `feature/storyforge-persistence-foundation`. A subsequent documentation-only commit records this identifier.

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


## Historical proposed v2 integration plan - superseded for product review (2026-11-05)

Planning only: persistence implementation/worktree remain intact. No API, LangGraph or provider changes are authorized by this plan. Recommendations below require approval before implementation.

1. **Composition and creation.** Add an injected application service between `api/routes_v2.py` / request execution and `StoryRepository`, with engine/session disposal in application lifespan. Persistence remains explicitly opt-in; no LangGraph routing/checkpointer changes are needed. Preflight with the existing pure v2 normalizer and exactly the same immutable profiles, settings, PagePolicy and quality rules used by the request-local engine; do not duplicate validation rules. Schema/policy/admission rejection creates no record and stores no rejected input. After successful preflight, call create (pending), then start (processing), and invoke the existing bounded public engine through the disconnect-aware execution boundary. Database initialization/create/start failure returns a sanitized storage-unavailable response before any provider call.

2. **Completion and failure.** After existing response-correlation checks, pass only a genuine `GenerationSuccessV2` and the captured brief to complete. Pass terminal `GenerationFailure` to fail: persist failed status, stable error code and allowlisted usage only, never draft, prompt, error message or raw diagnostics. Preserve existing generation error HTTP mappings. Cancellation/disconnect needs bounded, awaited terminal recording integrated with existing request cleanup, with no detached job. Process crash or failed cleanup may leave pending/processing; do not invent automatic recovery. If completion commit fails or its outcome is ambiguous, do not report the story as saved or rerun generation. Proposed response: sanitized HTTP 503 with a distinct persistence error code, known story ID and explicit no-automatic-generation-retry semantics; GET can resolve a committed record. Durable POST idempotency remains a separate requirement before enabling client retries.

3. **Atomic pages and transactions.** Keep provider execution outside database transactions. Create, start, complete and fail each own a short independent transaction. Complete writes accepted header, safe metadata, all N ordered sentence-unit pages and completed status atomically; any failure rolls the entire operation back. Existing domain/context checks and page PK/uniqueness/FK constraints remain authoritative at their respective boundaries. No intermediate draft pages are stored. Page count remains explicit user input and independent of age.

4. **Retrieval and concurrency.** Add an application read service mapping repository snapshots into a typed saved-story response. Extend the detached read DTO with creation time and sanitized failure code as needed. Retrieve by UUID; completed responses reconstruct StoryV2 from header plus pages ordered by page_number. Pending/processing/failed responses contain status only plus approved safe metadata, never draft content. Keep conditional status updates (one winner), shared row-lock reads and transaction rollback behavior. Configure statement/lock timeouts; no automatic generation retry on deadlock or storage errors. Do not add a queue, polling worker, list/search route or recovery job in this phase.

5. **Ownership and privacy before production.** Initial integration is restricted to controlled local testing with synthetic data. A UUID is not authorization. Before real child data or public saved-story routes: establish authenticated adult ownership and enforce it in every read/write query, add/migrate a genuine owner FK, and define retention/deletion, consent, TLS/encryption, backup access and log redaction. Do not invent identities. Preserve minimal request storage and exclude credentials, guidance, interests, pronouns, raw exceptions and rejected drafts. Review personalized themes/targets/content as sensitive; never log DSNs, validation inputs or returned stories. No unauthenticated public retrieval.

6. **Proposed frontend/API contract.** Preserve v1 and default unsaved v2 behavior. Recommend an explicit `save=true` query option on POST `/v2/stories/generate`, rather than changing the domain generation request. For saved success, add a persistent `story_id` in an API-only response DTO while retaining inline story/quality/usage; distinguish it from the existing request correlation ID. Saved generation failures may include story_id in their sanitized error envelope. Propose GET `/v2/stories/{story_id}` with lifecycle status, created_at and accepted story only when completed; use a consistent 404 for missing/inaccessible records once ownership exists. Update OpenAPI and TypeScript DTOs together after approval. Frontend saves the UUID, renders sentence_units in page order with existing direction metadata, and disables automatic POST retries. No frontend changes in the persistence implementation step.

7. **End-to-end validation.** Add FastAPI ASGI tests with fake providers plus real PostgreSQL for preflight/no-write rejection, successful create/start/complete/read, 27-page Hebrew target/page order, English and Unicode, and all terminal provider/quality/budget/deadline/cancellation failures. Fault-inject storage failures before generation, mid-completion and at ambiguous commit; assert rollback, sanitized responses and unchanged provider-attempt counts. Test disconnect/ASGI task cleanup, concurrent completions/read consistency, failed/rejected draft exclusion, save-disabled compatibility and v1 regression. Cover future ownership denial with no existence/content leak once authentication is separately approved. Keep PostgreSQL tests explicitly opt-in and distinguished from SQLite/mocked tests; run the full regression suite and package builds after implementation. No live AI calls.

**Approval requested before implementation:** approve the service/composition boundary, opt-in save and retrieval contracts, storage-failure/503 behavior, bounded cancellation handling and synthetic-local-only access restriction. Ownership/authentication and durable idempotency are prerequisites for their respective production behaviors, not implicitly included implementation milestones. Current test evidence remains 14 PostgreSQL / 773 total passing from the preceding implementation; this documentation-only plan adds no executable changes and does not claim new workflow tests have run.

## Initial Phase A product design handoff (2026-11-05; see later revision)

Scope authorized: concrete domain/ERD/API/module/migration/dependency design only. Phases B (schema/domain services), C (API integration) and D (implementation verification) are blocked on design approval; shared API changes additionally require approved branch reconciliation. No migration files, code, dependencies, fixtures, database contents or other worktrees changed during Phase A. Existing persistence worktree and implementation are intact on `feature/storyforge-persistence-foundation`, starting this task at `73ac933`.

Identify the Phase A design commit with `git log -1 --format="%H %s" -- docs/DATABASE_SCHEMA.md`; the Phase A delivery includes that commit ID. No merge, cherry-pick, push or deployment was performed.

Deliverables:

- `docs/ARCHITECTURE.md`: proposed Product/Template/TemplateVersion/Personalization/Book/BookPage/Asset model, three-mode service flow, strict documents and safe deterministic rendering, exact module boundaries, competitor behavior references and branch dependencies; implemented engine history retained below it.
- `docs/DATABASE_SCHEMA.md`: ERD; normalized catalog/localization/media/version tables; common private Books; keys/FKs/indexes/checks; aggregate immutability; revision/locking rules; additive proposed 0002/0003 migration and explicit optional backfill/rollback.
- `docs/API_CONTRACTS.md`: proposed v3 inventory, named request/response DTOs with Hebrew/English samples, schema-driven personalization, previews, manual edits, source-only AI adaptation, concurrency/error headers and OpenAPI/test requirements. V1/v2 remain unchanged; generated OpenAPI will be implemented only in Phase C.
- This handoff: current design status, scope, risks and approval decisions. These are the only four changed files in Phase A.

Principal decisions proposed: keep accepted stories/story_pages as AI source records; create common Books only for accepted AI or deterministic template/manual creation; source+Book completion shares one transaction; individual Books retain rendered snapshots and pinned origin; published template aggregates/media are immutable; customer-ready finalized Books remain private; draft editing uses parent revisions and atomic page permutations; template page-count variants are finite authored sequences; preview inserts no private records and invokes no AI. Future illustrations/exports attach to asset/document interfaces; no commerce/auth system or job queue is prebuilt.

Dependency evidence (read only): Agent 1 `7105be9` / diagnostics implementation `ec33b93`; Agent 2 `c2b72c2` / frontend `d961b6f`; Agent 4 `4dca2ac` / QA `136296c`. Their handoffs/contracts were inspected from their existing worktrees. They share base `5ae24e9` but are not merged here. Diagnostics add safe metadata not retained by persistence's existing allowlist; frontend consumes mock-first v2 StoryV2 only; QA covers offline HTTP, not the new product workflows. Required integration branch/merges must be approved before shared routes are changed. Do not sum isolated branch pass counts or overwrite another agent's handoff. Agent 2 owns new catalog/editor UI and Agent 4 owns independent QA; no agent was spawned or messaged by this work.

Security/release gates: private APIs are disabled by default, synthetic loopback-only until a real owner model exists. UUIDs do not grant access. Before production, authenticated adult ownership must cover Book, linked generation, private assets, previews and every list/read/write; existing ownerless records need quarantine/backfill policy. Minimize child data, preserve literal rendering/no executable templates, refuse arbitrary media URLs and unsafe controls, and restrict logs. Retention/erasure must include duplicated source and edited content. No production security certification is claimed.

Approval checklist:

1. Approve additive common Book schema and separate generation/catalog/finalization lifecycles, rather than repurposing stories.
2. Approve v3 product routes/DTOs and no changes to existing v1/v2 routes; confirm private-local-only availability and future owner prerequisites.
3. Approve sealed template versions, field schema/localization, bounded literal/field/select AST, externally referenced immutable assets and finite page variants.
4. Approve transaction-aware repository internals preserving existing standalone APIs, revision/ETag editing, shared-lock reads, storage ambiguity/no-retry behavior and trigger-based publication/finalization invariants.
5. Set server policy limits for page/block/document/schema/preview sizes, authoring permissions, content review and retention. Age recommendations do not determine page count.
6. Approve an integration branch and explicit merge ownership/order; optional historical backfill needs its own go/no-go because 0001 lacks full historical constraint/profile snapshots. Durable idempotency, real auth, media uploads, exports, public sharing and commerce are not silently authorized.

Phase A validation: read existing domain/API/persistence contracts and other agents' documented interfaces; visited the three specified Wonderbly pages for general catalog/personalization/preview behavior only. No proprietary content or artwork copied. Parsed all **8 fenced JSON examples** successfully, verified **16 local Markdown link targets**, checked balanced code fences and `git diff --check`. Mermaid relationships were manually reviewed, not rendered by a Mermaid tool. These are documentation checks, not validation against unimplemented Pydantic/OpenAPI schemas. No application tests or PostgreSQL tests are newly claimed for this documentation-only design. Prior accepted evidence remains **14 real PostgreSQL cases / 773 total** from commit `6cc8ef9`; no frontend-to-backend E2E coverage exists on this branch. Phase D requires new unit/rendering/versioning/API/manual-edit/concurrency/security/Unicode/rollback/migration tests with real PostgreSQL, fake-only AI compatibility and a final combined regression run after approved integration.

## Anonymous access and usage design delta (2026-11-05)

User accepted overall architecture in principle and requested these document revisions only; Phase B remains on hold. Starting revision commit: `70b86d2277baadec6ea2b1ce4b27e7807d9693da`. Only ARCHITECTURE.md, DATABASE_SCHEMA.md, API_CONTRACTS.md and this handoff change. No source, dependencies, migrations, database contents, branches of other agents or review ZIP are changed. The existing ZIP is the earlier snapshot, not this revised design.

Design delta:

1. **Anonymous is an owner, not a public library.** Registration-free visitors receive a server-issued opaque cookie, principal, CSRF context and expiry. Every Book/story/image/operation/media query is owner-scoped; UUID knowledge is insufficient. Rotation keeps the same principal/allowance. Session loss cannot recover by resource ID. No child identity is invented. Future account claim requires verified account + anonymous possession/login-bound proof, atomically links the namespace and revokes guest credentials; pending work and existing asset/source ownership stay consistent without rewriting every resource.
2. **Ten story units and ten image units daily, separately.** Proposed UTC calendar day, database time after admission lock; reserved slots count immediately. One story engine run including allowed attempts/repair is one story unit; one requested output image is one image unit, and regeneration is new work. Existing per-request budgets/quality/retry/provider protections stay. Manual/template rendering/editorial media/retrieval use no AI units. A quota is not a dollar budget.
3. **Explicit failure/refund policy for approval.** Daily allowance counts creation attempts reaching dispatch, including provider refusal/error/unsafe output/timeouts/cancellation or failed persistence. Pure validation/policy rejection before dispatch does not consume. Release a reservation only with proven pre-dispatch cancellation/failure and a fence preventing later send; unknown send/worker death never automatically refunds. Explain this to customers as attempts, not guaranteed successful books/images.
4. **Durable atomic admission, no quota reset on claim.** PostgreSQL principal gates + daily capability buckets + unique operation/reservation/idempotency records serialize concurrent pods. Claim-aware scope includes account and claimed namespaces; combined usage may exceed ten and leaves zero remaining, honoring already admitted work. Original admission day stays charged after midnight. Duplicate replay/settlement never double-counts/refunds. Single authoritative writer per principal, no per-pod or eventually consistent counters; quota outage fails closed. Additional session issuance/network-prefix burst controls, bot challenge, in-flight and global spend caps mitigate cookie-reset/Sybil abuse without requiring registration. Ten per anonymous principal cannot honestly guarantee ten per human.
5. **Preview remains temporary.** Catalog/schema/public samples need no session/account. Personalized previews need only anonymous session/CSRF, render in memory with no saved Book/choices/AI unit and no public personalized URL. Explicit from-template save creates a scoped private Book. Optional raster cache requires separate TTL/access approval. Expired-session access and sensitive-data retention/deletion remain different policies.
6. **Additive v3 and legacy coverage.** Add proposed session/claim/usage/image/operation contracts; v3 AI requires Idempotency-Key. Preserve existing generation payloads, engine responses and source tables, but public legacy routes must share admission rather than remain a bypass. New gate 401/403/429 behavior uses existing legacy failure enums plus documented headers; this transport change requires Agent 2/4 compatibility review. Frontend must move from credentials:omit to same-origin cookies, in-memory CSRF, one key per intentional creation, separate quota displays and session-scoped views, with no signup wall or silent paid retry.

Proposed schema additions (not migrations): access_principals/access_sessions/principal_claims, owner FKs for Books/source stories/private assets, creation_operations/daily_usage_buckets/quota_reservations and image_generations. Existing ownerless source rows are quarantined, never claimed by first reader. Proposed 0004/0005 labels require coordination, not a numbering commitment; no file beyond actual 0001 exists. Future durable async input envelopes may require encrypted short-lived storage, but current minimized request metadata must not be expanded casually to raw prompts.

Agent 1 dependency inspection: initially no async artifact existed; during this revision Agent 1 published `docs/AI_GENERATION_RELIABILITY_DESIGN.md` in commit `19d63f7` on `docs/ai-generation-reliability-design`. It was then inspected read-only. It recommends durable whole-book jobs first, backend-owned ownership/idempotency/leases/finalization and optional chunk evaluation requiring separate budgets. Its no-product-DB/no-Agent-3-design statements reflect its isolated baseline; this worktree has the accepted foundation. Anonymous principal scope must satisfy its owner boundary without requiring registration. Required joint decisions: one operation/idempotency/admission ledger; a separate proposed `/v3/jobs/stories` 202 path sharing operation IDs/keys with synchronous creation; atomic source/outbox acceptance; lease/fencing and actual first-attempt dispatch journaling; retries without fresh budgets; queue expiry/deadline and cancellation/disconnect policy; unknown-send recovery; quota settlement; image safety; encrypted engine-private input/validated-plan/chunk retention. Chunking remains unapproved and never makes extra creation units a license for extra attempts. Never store internal partials as completed source/Book pages. Agent 1 owns engine/provider reliability; Agent 3 proposes shared backend owner/job/accounting/persistence ports; exact worker/backend contracts remain jointly reviewable before implementation. Agent 2 needs session/usage/preview/result contracts; Agent 4 must test isolation, CSRF, quota/claim races, clocks and approved async recovery. No branch was merged here.

Follow-up inspection: Agent 1 then committed `docs/AI_BACKEND_INTEGRATION_CONTRACT.md` at `e34b588`, explicitly reading an intermediate copy of these documents and recognizing anonymous ownership/accepted persistence. Read it without modifying that branch. Adopted clarification: fingerprint canonical client input only, with server configuration/profile/prompt/pricing versions frozen separately, so deployment defaults cannot break replay. Its cancelled operation state (source failed/CANCELLED) is a compatible proposal requiring approval. Transport remains an explicit choice: its negotiated v3 async 202 versus the separate job-route candidate here. Worker hosting/access/operation persistence are Agent 3 responsibilities; engine retry/resume ports stay Agent 1-owned, with joint journaling/fencing contracts. Restricted diagnostic allowlist changes and image-provider scope are not implicitly approved. Agent 1's working-copy hashes are historical snapshots, not final-document hashes or mutual approval.

Remaining decisions for approval (the product's ten-per-capability limit and registration-free creation are fixed requirements):

- UTC calendar boundary versus another explicitly server-controlled product timezone; attempt-counting and narrow proven-pre-dispatch refunds.
- Session idle/absolute TTL (proposed 7/30 days), rotation/revocation behavior, retention of inaccessible anonymous content, and future claim proof through login.
- Idempotency replay lifetime (pending + proposed >=48h terminal), operation/input retention, image input/output caps and safety contract; no auto-retry promise.
- Adaptive abuse thresholds, network-digest retention/rotation, bot-challenge privacy/accessibility and shared-network fairness; global spend/capacity policies stay separate.
- Agent 1 async/sync choice, operation states/ownership, worker/outbox/fencing/cancellation, and a coordinated legacy client/session-gate rollout. No unreviewed job queue, auth provider, image adapter, production deployment or Phase B implementation is approved by this delta.

Verification for this revision: all **9 fenced JSON examples parsed**, **16 local Markdown link targets resolved**, code fences balanced, Mermaid manually reviewed (not rendered), `git diff --check` passed, and scope verified as only the four requested Markdown files. OWASP session/CSRF and PostgreSQL 17 timestamp/conflict documentation are linked next to the relevant design choices. No application, quota, session, image, claim, distributed or browser E2E tests were run or newly claimed. Historical foundation evidence remains 14 real PostgreSQL / 773 total tests; it does not validate the proposed access/admission model. Identify this revision commit with `git log -1 --format="%H %s" -- docs/DATABASE_SCHEMA.md`. Stop for review after documenting the delta.
