# AI engine / backend integration contract

Status: **revised after conditional review; design only**. Reviewed 2026-11-05.
Agent 1 owns generation; Agent 3 owns product APIs, access and persistence.
No implementation, shared DTO, database migration or runtime change is authorized.

## Sources and reconciliation

This reconciles [the engine reliability design](AI_GENERATION_RELIABILITY_DESIGN.md)
at `19d63f7` with Agent 3's **latest committed** Phase A revision in the
persistence worktree, branch
`feature/storyforge-persistence-foundation`, HEAD `7e38326`:
`docs/ARCHITECTURE.md`, `docs/API_CONTRACTS.md`, `docs/DATABASE_SCHEMA.md` and
`docs/PERSISTENCE_HANDOFF.md`. Agent 3 committed this revision during review;
all four were rechecked against that commit without modifying its clean worktree.
Their SHA-256 snapshots are:

| Document | SHA-256 |
| --- | --- |
| ARCHITECTURE | `696adf5ebdc03c8a20f399fd26afa1040c864c303f573fa267ccae3bb43f2797` |
| API_CONTRACTS | `59bcb274b6add4b293ad6b4fb30dade8b6c1a7990bb7016caf592f623f43f80d` |
| DATABASE_SCHEMA | `62503ce777e3b1b396e7a2f8771d6393c9f0f8b9a7878b86045e93d544c24dd9` |
| PERSISTENCE_HANDOFF | `6d0118b10b96fbec9a6bebfe4479a448443fa4763ab068096c745890cf1ab013` |

The user supplied Agent 3's conditional review and required refinements; this
revision incorporates them, without claiming final Agent 3 sign-off. Latest Phase
A now proposes separate sync/async routes, admission-time configuration freezing
and coherent first-dispatch accounting. Those replace this contract's earlier
negotiated-route proposal. Older account-required and `save=true` proposals remain
superseded. Remaining document differences and approvals are listed below.

## 1. One durable operation lifecycle

Use Phase A's `creation_operation` as the generation job identity, linked to
exactly one source generation and one quota reservation. Do not add a competing
job/admission ledger. Engine attempt records are subordinate to this operation.

| Operation transition | Required condition / atomic effect |
| --- | --- |
| admitted -> queued | Persist operation, idempotency, daily reservation, pending source, dispatch intent and immutable admitted execution snapshot together; rollback all on failure |
| queued -> processing | Atomically claim lease/fencing token, start the pending source and set first-processing time/active expiration exactly once |
| processing -> processing | Safe phase updates or bounded recovery under the same ledger; never fresh admission |
| processing -> completed | Accepted full result; source completion, initial Book/pages, operation result and terminal settlement commit in one unit of work |
| queued/processing -> failed | Persist fixed safe error/stop reason and settle reservation; no Book or deliverable partial draft |
| queued/processing -> cancelled | Explicit authorized cancellation wins an atomic terminal-state decision; dispatch fences and settlement apply |

`admitted` is a transaction event, not a separately observable durable state.
Public states are `queued`, `processing`, `completed`, `failed`, `cancelled`.
Phase A source status remains `pending/processing/completed/failed`; cancelled
operations map to source `failed` with safe cancellation code. Book lifecycle
remains `draft/finalized/archived`. None of these means public publication.

Processing phases: planning, writing, retry_wait, checking, finalizing. Report
phase and verified page counts, not invented completion percentages or drafts.
Lease loss is not permission to replay an uncertain provider send. Fence stale
publication; preserve uncertain attempt/cost reservations. Restart recovery must
load a versioned engine snapshot, not call today's fresh `generate` as a resume.
That resume capability does not exist yet; fail safely until explicitly built.
Freeze at admission: canonicalization/request interpretation, resolved developmental
profile and page/density constraints, generation mode, provider/stage models,
prompt/output schema/rubric versions, capability/pricing versions, retry policy,
attempt/repair limits, per-call and aggregate token/cost allocations and deadline
duration. Store versioned references plus sufficient immutable data to reproduce
them, excluding credentials. First processing starts that frozen duration; a
redeployment, claim or lease renewal cannot substitute new defaults. If a frozen
artifact is unavailable or revoked for safety, fail closed rather than upgrade it.

## 2. Idempotency and duplicate prevention

Adopt Phase A's required bounded random Idempotency-Key for new AI operations,
scoped to capability and authorized issuance namespace, searched across claimed
namespaces. Store keyed digests only. Fingerprint the canonical validated request;
freeze resolved engine/profile/prompt/schema/pricing versions separately on first
admission. A later deployment must replay the original operation, not produce a
conflict merely because server defaults changed. Explicit client policy/version
fields, if ever supported, belong in the request fingerprint.

Same key/request returns the same operation or accepted result without new work
or daily charge; changed request or ambiguous claimed-namespace collision -> 409.
Check replay before new admission capacity checks (after current authorization).
Atomic uniqueness/claims prevent duplicate operation creation; fenced attempt
authorization prevents independently scheduling the same slot. Unique source
linkage and atomic finalization prevent duplicate initial Books. Neither promises
exactly-once provider delivery/billing across a crash or network partition.
An ambiguous commit is resolved by authorized lookup, never automatic regeneration.
New deliberate regeneration uses a new key and quota unit. Phase A's pending
lifetime plus >=48-hour terminal retention is proposed, not approved. Document
loss of replay guarantees after expiration; no automatic new-key retry.

Persist the canonicalization version, input schema version and digest key versions
with the operation. Route/transport is excluded from the story capability key and
request fingerprint. For replay, locate the authorized stored key first, then
validate/canonicalize against its frozen interpretation, before applying new-job
capacity or current-version validation. Never re-normalize historical requests
using today's defaults. Bound body parsing before any lookup.

Retain verification keys/compatible canonicalizers for the entire live operation
and replay window. Rotation writes with the new key but searches/verifies retained
versions under the same principal gate; no raw keys or sensitive input hashes in
logs. Missing verifier/key -> safe admission-unavailable response, no work. If an
old interpretation cannot be supported, return proposed fixed 409
IDEMPOTENCY_VERSION_UNSUPPORTED with authorized operation reference only; never
reinterpret as a fresh creation. Existing status/result reads remain available
under current access policy and supported result readers.

If a result is erased during the replay window, keep a minimal authorized
key/operation tombstone and return proposed 410 RESULT_DELETED, no content or new
generation. Deleting a Book does not restore it from immutable source on replay.
Required erasure must also cover private source/snapshots; tombstone retention
needs privacy approval. After replay expiry, deduplication is no longer promised;
clients must not retry old keys automatically. Source/book deletion does not reset
quota or erase active accounting. New public error names here require Agent 3 DTO
approval and do not extend legacy domain enums.

## 3. Anonymous generation and private access

Use Agent 3's anonymous principal/session, not an account requirement or caller
owner ID. Its proposed 256-bit opaque Secure/HttpOnly host-only cookie, keyed
server digest, CSRF and exact-origin checks cover creation/cancellation. Private
polling, books and asset delivery require current principal authorization; UUIDs
alone confer no access. Missing/foreign resources share 404. Responses are
no-store; no credentials, child content or bearer grants in URLs/logs.

Rotate credentials without changing principal or quota. Session expiry/loss
does not transfer ownership, reset counters or authorize recovery by resource ID.
Workers receive an immutable issuance principal/operation ID, never browser
cookies. Losing a browser connection or session must not silently create a new
generation. Abuse limits and global spend/concurrency controls remain separate
from ownership and daily quotas; anonymous sessions do not establish unique humans.

## 4. Registration and ownership transfer

Follow Phase A's namespace claim rather than bulk rewriting resource owners:
verified account + fresh anonymous possession proof + CSRF/login-bound consent
atomically claim the anonymous namespace, revoke guest credentials and rotate
account access. Claim is single-winner and cannot move to a second account.
Existing source, operation, Book and asset owner IDs remain stable; account scope
includes claimed namespaces. New writes use the canonical account principal.

Queued/in-flight work retains operation, admission day, attempts, reservations
and deadline; only authorized result access changes. Aggregate existing and
claimed usage, even above the daily allowance; do not refund/reset or cancel
already admitted work. Reads, claim, dispatch authorization and settlement must
use Agent 3's canonical-principal lock order. Exact login proof handoff, retention
and shared-device UX remain Agent 3/auth approval dependencies.

## 5. Accepted source -> canonical Book/BookPage

Only a genuine accepted `GenerationSuccessV2` creates the initial AI Book.
Agent 3's transaction-aware unit of work completes the immutable source and
creates its unique initial editable Book, all pages and operation linkage together.
Never call independently auto-committing repository wrappers inside that unit.
Require identical immutable issuance owner IDs on operation, source and initial
Book; account claim changes authorization scope, not these IDs. Validate the
accepted result against that operation's frozen request/constraints before mapping.

Before admission/provider dispatch, validate canonical PageDocument capacity:
requested N, title/text limits, maximum sentence-unit count and bounded string/
encoded-document sizes, block count and text-only layout/language support. Agent
3 supplies a versioned canonical-capacity policy; Agent 1 supplies bounded output
contracts and allocation estimates. Word/token estimates alone cannot prove byte
fit: tighten admitted schema bounds or reject if worst-case representation exceeds
capacity. Never truncate accepted output to fit storage. Repeat exact canonical
validation after generation, before atomic persistence; an invalid projection
creates no Book and cannot trigger a fresh AI run automatically.

| Engine source | Phase A canonical projection |
| --- | --- |
| Accepted title/language/direction | Book title/language/direction; mode AI_GENERATED; initial state draft/revision 1 |
| Source generation ID | Unique Book source_story_id; no template source or personalization record |
| page_number | Contiguous one-based BookPage position, exactly requested N story pages |
| page_id / target_id | source_page_key / nullable source_target_id; backend allocates separate stable editor UUID |
| sentence_units | One PageDocument v1 text block, preserving unit order, exact Unicode and language/direction |
| Profile/constraint/check/policy versions | Typed source snapshot; source quality applies to initial revision only |

No new illustration, cover page, translation or layout padding is implied.
Covers/print sheets do not count toward requested N. Subsequent edits change
BookPages, not the approved source or its original gate result. TEMPLATE_BASED
and MANUAL produce the same Book/PageDocument through Agent 3's paths without
AI source records or fabricated usage. Canonical fields/DTOs remain Agent 3-owned.

## 6. Daily quota is not provider-call capacity

Phase A proposes separate ten-story/ten-image UTC daily allowances. One admitted
story consumes one story unit, including its permitted internal retries; it does
not grant unlimited calls or guarantee success. Keep quota policy outside graph.
Reserve at admission; consume once at durable first-dispatch authorization;
release only proven pre-dispatch cancellation/failure with dispatch fenced.
Unknown sends/dispatched failures remain consumed. Settlement is idempotent and
uses original admission day across midnight and ownership claim.

Engine admission independently enforces attempt, token, USD and time limits.
Reserve each attempt before sending and enough capacity for mandatory remaining
calls. Current whole-book workflow needs Planner + Writer = 2 calls under the
global maximum 3; at most one recovery slot remains. A quality rewrite consumes
that same capacity, not an additional allowance. Four chunks would need 5
mandatory calls and cannot run under today's limit, even with daily quota left.
Backend redelivery, account claim and disconnect cannot reset engine accounting.
Keep unknown token/cost usage conservatively reserved, never zero.

### Durable dispatch protocol

1. At each provider boundary, verify current operation state, lease/fence, frozen
   policy, cancellation, active deadline and mandatory remaining-call capacity.
2. In one short backend-owned transaction, durably insert the unique attempt ID,
   stage/slot, input/output token and USD reservations, and dispatch authorization.
   For the first attempt also consume the reserved daily unit exactly once. A
   rollback or uncertain commit permits no speculative send; reconcile by ID.
3. After confirmed commit, the current worker sends that authorization at most
   once, with SDK retries disabled. Record safe outcome/usage or outcome-unknown
   durably; subsequent attempts repeat step 1 under the same global ledger.

The persisted journal is authoritative; engine in-memory accounting must mirror
it through an approved port, not become another independently mutable ledger.
No transaction/DB lock spans provider I/O. Fencing can reject a stale worker's
future authorizations, writes and publication; it cannot recall an authorized
request or completely close the commit-to-network race. Once dispatch is
authorized, conservatively count the unit/slot even if a send cannot be proven.
Release only if authorization never committed and all potential senders are
fenced. A lease timeout alone proves neither non-dispatch nor non-billing.

### Unknown outcomes and finalization recovery

Never automatically replay an uncertain provider send or restart the engine.
Preserve its attempt/token/cost reservation and consumed daily unit. Initially,
mark the operation failed with an approved safe unknown-outcome discriminator;
do not label it a confirmed provider rejection or monetary-budget failure. Late
trusted accounting may reconcile usage, never reopen the job or publish content.
Known terminal provider responses may still use the existing bounded retry policy.

An engine-accepted complete result is different from an uncertain provider send.
Persist its encrypted, schema/quality-validated finalization envelope with an
integrity digest, owner/operation/fence, frozen versions, acceptance time and safe
ledger before finalization. No raw provider response, prompt or rejected draft.
Propose a fixed 15-minute recovery window from durable acceptance (not renewed).
During it the job remains processing/finalizing, not completed or a public Book.
Authorized recovery rechecks cancellation, ownership, digest, schema and linkage,
then retries only the same atomic source/Book/operation transaction. It performs
zero provider calls and creates no new attempt, daily unit or execution budget.
Resolve an ambiguous finalization commit by operation/source lookup first.

The active deadline still bounds AI work and ordinary generation; this separately
approved persistence-only window may outlive it after timely engine acceptance.
It never authorizes more generation. If acceptance is not durably captured, fail
without regenerating; if the window expires, fail safely and erase the envelope.
After confirmed completion or cancellation delete it promptly. Neither storage
recovery nor cleanup can reset attempt accounting or turn a terminal failure into
a second generation. This requires new ports and privacy approval, not current
engine functionality.

This durable finalization-recovery envelope applies to the async job path. Keep
Phase A's synchronous connection-bound cleanup and safe 503
PERSISTENCE_UNAVAILABLE/save_outcome behavior; do not detach a sync request into
background recovery. A committed result can be resolved by authorized lookup.
Extending durable recovery to sync execution requires separate explicit approval.

## 7. Retry, deadlines, cancellation and safe status

Proposed retry hardening follows the reliability design: bounded exponential
equal jitter (base 1 s, ceiling 8 s), honoring longer valid provider Retry-After;
one shared scheduler, no SDK/node/worker retry multiplication. These coefficients
are pending approval and are not implemented here. Transient transport retries
preserve the semantic request; schema repair and quality repair are distinct
bounded actions. Check cancellation, remaining mandatory work, money and time
before waits and dispatch. Never extend expiration to accommodate backoff.

Queue expiry is separate from active execution expiration. Freeze the latter at
first processing, persist UTC expiration and derive local monotonic remaining
time; retries/restarts do not restart it. Existing isolated test values remain
45 s/attempt, 135 s/operation and $0.075, not new production defaults.

Explicit cancellation fences future sends and cooperatively cancels/drains local
tasks; an already submitted call may still bill. Completion versus cancellation
is decided atomically; completion winning never deletes the accepted Book.
Public cancelled is terminal. Repeated cancellation returns the same terminal
status without new work/refund; cancellation of completed work returns completed
with its existing Book. Cancellation winning fences finalization and prevents
late Book publication. Late safe usage reconciliation is allowed without state
reopening. Browser disconnect, session expiry/revocation or account claim do not
cancel a durable job. They may revoke result access. Existing synchronous v1/v2
disconnect cancellation stays unchanged; the proposed synchronous v3 path retains
its documented connection-bound behavior. Cancellation route/DTO is Agent 3-owned
and requires approval. Shutdown stops new claims and preserves uncertain work.

Public job status exposes approved fixed error code/stop reason and result IDs,
not attempt details. Keep sanitized per-attempt category/upstream HTTP status in
restricted execution metadata. Extend Agent 3's persistence allowlist explicitly;
its current allowlist excludes these new diagnostics. Never include raw provider
errors, prompts, URLs, headers or credentials. Distinguish provider unavailability
from attempt exhaustion, money exhaustion, deadline, malformed output and quality
failure; preserve existing v1/v2 error enums/mappings.

## 8. Long-book admission and recovery boundary

Retain whole-book Writer and the four nodes initially. N is explicit, independent
of age, with configurable service range currently 1-32. Range validation is not
capacity admission: Planner allocation is `200 + 96*N`; N=32 needs 3,272 output
tokens, exceeding the isolated runtime's 3,000 Planner cap. N=27 needs 2,792 and
fits that cap. Age/density also affects Writer/cost admission. Reject infeasible
requests before quota consumption/provider work; never clamp N or lower density.

Sequential chunking remains an unproven evaluation candidate requiring private
chunk/resume contracts, global outline/continuity, exact educational ranges,
whole-book assembly/gating, and a separately approved global execution policy.
Do not advertise universal 32-page readiness or implement chunks under today's
three-call limit. Persisting validated private plans/chunks requires explicit
privacy approval; the minimized existing source record cannot replay a request.

## 9. API and module responsibility

| Owner | Boundary |
| --- | --- |
| Agent 1 | Domain generation contracts, normalization/admission estimates, four-node graph, prompts/gate, provider adapters, attempt ledger and future private resume contract |
| Agent 3 | Canonical Book/PageDocument, access/claim, daily quotas/idempotency, operation persistence/leases/fencing, worker hosting, v3 DTOs/routes, transactional source/Book completion and authorized reads |
| Joint review before coding | Typed worker/engine ports for frozen input, dispatch reservation, snapshot/progress, accepted/failure result and cancellation; one durable accounting authority |
| Agents 2/4 with owners | Client session/idempotency/polling migration and combined offline/API/PostgreSQL race verification |

Agent 3's `application/ai_books.py` composes access/admission and injected engine;
it does not implement provider retries or gate rules. Engine imports neither ORM
nor HTTP/session contracts. Proposed backend admission hooks (`admit`,
`authorize_first_dispatch`, `settle`) and engine reservation journal must commit
coherently before dispatch, without a database lock held over provider I/O.
Use Agent 3's transactional store/worker boundary if approved; no Redis/Celery
or second queue is implied. Image generation remains a separate unimplemented
capability, not an added story node or authorization under this contract.

Adopt separate proposed routes; **async is the primary frontend target**:

| Route | New operation | Existing matching key, from either route |
| --- | --- | --- |
| POST `/v3/jobs/stories` | 202 with operation reference, Location `/v3/operations/{id}` and polling Retry-After | 200 current OperationStatus + same Location, including terminal result reference; no enqueue or AI work |
| POST `/v3/books/ai` | Synchronous execution; 201 Book response on atomic completion, safe error on failure | Completed with accessible Book: 200 same Book/source reference; queued/processing: proposed 409 OPERATION_IN_PROGRESS + operation Location without attaching a second runner; failed/cancelled: replay safe terminal outcome without execution |

Both use unchanged StoryRequestV2 bodies, story_generation capability and the same
authorized namespace/key/fingerprint scope. Transport switching never starts a
new execution or changes the first-admitted disconnect/deadline policy. Async
polling disconnect does not cancel; replaying a sync job through async does not
convert its lifecycle. Deleted/version-unsupported cases follow section 2.
Use Retry-After for polling guidance, never automatic creating-POST retries.
Agent 3 owns exact DTOs, replay status/error mapping and cancellation endpoint
(candidate POST `/v3/operations/{id}/cancel`); document these before API work.
Operation polling is authoritative for execution; GenerationStatus is a scoped
source projection, not a second scheduler. Current v1/v2 remain synchronous and
unsaved. Phase A's proposed public session/CSRF/quota gate for legacy routes is
an explicit transport compatibility change requiring coordinated rollout, not a
change already approved or implemented by this document.

## Proposed operational defaults: approval required

These are design candidates, not configuration edits, SLAs or permission to
increase provider limits. All TTLs use authoritative UTC timestamps; logical
expiry blocks access immediately, with encrypted payload deletion within 60 s.

| Decision | Proposed default / bound | Reason / qualification |
| --- | --- | --- |
| Queue expiry | 5 minutes from admission, never renewed | Bound waiting and reserved quota; expire failed before first dispatch, release only with proven dispatch fencing |
| Worker lease | 60 seconds; heartbeat every 10 seconds | Fits the isolated 45 s attempt with renewal; lease is not provider timeout or restart permission; all claims need fencing |
| Active execution | Frozen admitted duration starts once at first processing | Existing isolated 45 s/attempt, 135 s overall, three calls and $0.075 stay unchanged; other runtimes retain their configured limits |
| Request/validated-plan snapshots | Queue expiry plus admitted active duration at most; erase on terminal outcome, deletion within 60 s | Only encrypted minimum replay data; never raw output/failed draft; no indefinite TTL renewal or chunk storage approval |
| Accepted finalization envelope | 15 minutes from durable engine acceptance; erase on completion/cancellation or expiry | Storage-only recovery; zero AI calls after active expiry; sensitive envelope is distinct from ordinary snapshots |
| Idempotency metadata/tombstone | Entire nonterminal lifetime + 48 hours after terminal outcome | Matches Phase A minimum proposal; retain compatible verifiers/keys for at least this window; no child content in tombstone |
| Anonymous session | Idle 7 days, absolute 30 days; rotation never extends absolute lifetime | Matches Phase A; not a Book/source retention policy or a guarantee of cross-device access |
| Unknown-send recovery | Zero automatic provider replays | Terminal safe failure with held reservations; no refund/restart from lease expiry |
| Proven unsent queued work | Reclaim only with valid fence and unexpired queue TTL; same operation | No fresh allowance; never reclaim an authorized uncertain send for generation |
| Interrupted processing | No automatic generation resume initially | Requires a separately approved resume protocol; fail with conservative ledger if not safely finalizable |
| Finalization transaction recovery | At most 3 total transaction attempts, including original; waits 1 s then 2 s | Within fixed 15-minute window; reconcile ambiguous commits before retry; no provider work; exhaustion -> safe failure, erase envelope |

Snapshot expiry blocks further AI dispatch until the operation is safely failed;
minimum non-content ledger/idempotency evidence survives separately. The lease
values must be re-evaluated for any future attempt duration without changing an
already admitted job. Worker storage/clock outages fail closed. Book/source data
retention, backups, erasure handling and abandoned-guest cleanup remain explicit
privacy decisions; session TTLs do not silently set them.

Clock authority must be shared for admission/leases/expiry; workers derive fresh
monotonic remaining time after claim. Renewal cannot move active expiration or
revive an expired lease. A snapshot's logical expiry prevents new scheduling;
in-flight uncertain sends retain their ledger even when content is deleted.
The proposed short-lived encrypted stores must have approved backup exclusion or
equivalent bounded cryptographic erasure; a database row TTL alone does not
guarantee removal from replicas, backups or telemetry.

## Remaining blockers and Phase A reconciliation

Aligned with latest Phase A: separate sync/async paths, one operation/reservation,
namespace claims, UTC quota admission, first-dispatch consumption, atomic initial
Book projection, and unchanged legacy engine contracts. Agent 3's accepted 0001
source persistence exists in its branch; durable jobs/access and product Book
tables do not. No integration of that branch is claimed here.

Remaining differences requiring Agent 3's next document revision/sign-off:

| Difference | Resolution proposed here / approval still needed |
| --- | --- |
| Phase A leaves cancelled-versus-failed public status open | Public cancelled is required by this review; source remains failed/CANCELLED |
| Phase A lacks complete OperationStatus/replay DTOs | Adopt route matrix above, safe stop reasons and deleted/version-unsupported outcomes; Agent 3 owns shared DTO edits |
| Phase A operation table has no finalized job/lease/snapshot specification | Define ports and atomic durable journal before migration; no second job ledger |
| Phase A excludes diagnostic fields from stored safe usage | Approve restricted diagnostic allowlist separately; never add it to public polling |
| New recovery/TTL proposals exceed existing design detail | Approve the table, persistence-only window and privacy/deletion protocol; no setting is effective yet |

Implementation blockers:

1. Agent 3 final review of revised operation/route/replay states, cancellation API,
   historical-verification behavior and safe metadata; no unilateral DTO changes.
2. Anonymous session lifetimes, verified claim handoff, quota counting/release and
   idempotency replay retention; distinguish replay from deliberate regeneration.
3. Approved durable dispatch port, transaction/fencing fault tests, worker lease/
   clock/queue defaults and finalization-only recovery. No exactly-once external
   generation/billing guarantee is possible.
4. Encrypted short-lived request/snapshot storage, access, deletion and retention
   across source, editable Book, backups and abandoned anonymous resources.
5. Retry coefficients and future long-book capacity classes/chunk evaluation;
   today's models, limits and budgets remain unchanged. Approve integration base
   and merge ownership separately before combining agents' branches.

## Offline verification

Proposed joint offline acceptance: duplicate concurrent submissions; claim during
queued/processing/completion; old guest denied afterward; quota across UTC midnight;
crash before/after send and ambiguous completion commit; stale-worker fencing;
cancel/finalize races; no replay budget reset; source+Book rollback; lossless Hebrew
sentence-unit mapping; 27-page ordered targets; 32-page zero-call admission failure;
safe polling with no private draft or diagnostic leakage. Use fake providers and
synthetic data, plus Agent 3's opt-in database tests when implementation is approved.
Also test cross-route replay in every terminal/nonterminal state, canonicalizer/
HMAC rotation, erased-result tombstones, frozen admission across deployment,
PageDocument worst-case capacity rejection before dispatch, finalization window
expiry and bounded storage recovery with zero additional provider calls.

Verification for this task is document/source inspection and Markdown checks only;
all four latest Phase A document hashes, UTF-8/local links, balanced fences,
required decision sections and Planner arithmetic passed; git diff --check passed.
Application tests were not rerun for this documentation-only change, and no new
runtime or persistence behavior is claimed. No live AI calls, configuration
changes, shared code edits, merge, push or deployment. Wait for approval.
