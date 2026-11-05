# AI engine / backend integration contract

Status: **proposal for joint approval; design only**. Reviewed 2026-11-05.
Agent 1 owns generation; Agent 3 owns product APIs, access and persistence.
No implementation, shared DTO, database migration or runtime change is authorized.

## Sources and reconciliation

This reconciles [the engine reliability design](AI_GENERATION_RELIABILITY_DESIGN.md)
at `19d63f7` with Agent 3's **working-copy** Phase A revision in
`C:/Users/dvir3/storyforge-persistence`, branch
`feature/storyforge-persistence-foundation`, HEAD `70b86d2`:
`docs/ARCHITECTURE.md`, `docs/API_CONTRACTS.md`, `docs/DATABASE_SCHEMA.md` and
the historical `docs/PERSISTENCE_HANDOFF.md`. The first three are uncommitted;
they were read without modifying that worktree. Their SHA-256 snapshots are:

| Document | SHA-256 |
| --- | --- |
| ARCHITECTURE | `fe172774ae7a93e4c60d014b15347a5f3bce20339ee8f2d65cbcae6ae048d73a` |
| API_CONTRACTS | `31bd499544a8edcaca9bfcc9a6e88f5faccd5d146a2982bbfad4432febbc62fc` |
| DATABASE_SCHEMA | `25cf211d0072d40b1b15f1bf69527f9885e00ff937bc58ed4232e56ecb4d9315` |

No active Agent 3 session is available here. This is document-level coordination,
not Agent 3 sign-off. Its Phase A revision supersedes older account-required and
`save=true` proposals. Anonymous access is required; session lifetimes, quota
settlement details and async transport remain proposals requiring approval.

## 1. One durable operation lifecycle

Use Phase A's `creation_operation` as the generation job identity, linked to
exactly one source generation and one quota reservation. Do not add a competing
job/admission ledger. Engine attempt records are subordinate to this operation.

| Operation transition | Required condition / atomic effect |
| --- | --- |
| admitted -> queued | Persist operation, idempotency, daily reservation, pending source and dispatch intent together; rollback all on failure |
| queued -> processing | Worker claims a bounded lease with fencing/version token; freeze execution policy and expiration |
| processing -> processing | Safe phase updates or bounded recovery under the same ledger; never fresh admission |
| processing -> completed | Accepted full result; source completion, initial Book/pages, operation result and terminal settlement commit in one unit of work |
| queued/processing -> failed | Persist fixed safe error/stop reason and settle reservation; no Book or deliverable partial draft |
| queued/processing -> cancelled | Explicit authorized cancellation wins an atomic terminal-state decision; dispatch fences and settlement apply |

`admitted` is a transaction event, not a separately observable durable state.
Propose public states `queued`, `processing`, `completed`, `failed`, `cancelled`.
Phase A source status remains `pending/processing/completed/failed`; cancelled
operations map to source `failed` with safe cancellation code. Book lifecycle
remains `draft/finalized/archived`. None of these means public publication.

Processing phases: planning, writing, retry_wait, checking, finalizing. Report
phase and verified page counts, not invented completion percentages or drafts.
Lease loss is not permission to replay an uncertain provider send. Fence stale
publication; preserve uncertain attempt/cost reservations. Restart recovery must
load a versioned engine snapshot, not call today's fresh `generate` as a resume.
That resume capability does not exist yet; fail safely until explicitly built.

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
Atomic uniqueness/claims prevent concurrent duplicate dispatch and Book creation.
An ambiguous commit is resolved by authorized lookup, never automatic regeneration.
New deliberate regeneration uses a new key and quota unit. Phase A's pending
lifetime plus >=48-hour terminal retention is proposed, not approved. Document
loss of replay guarantees after expiration; no automatic new-key retry.

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
Polling disconnect does not cancel a durable job; existing synchronous v1/v2
disconnect cancellation stays unchanged. Cancellation route/DTO is Agent 3-owned
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

Recommend explicitly negotiated async `202` + operation Location/polling for new
v3 AI creation; retain proposed synchronous `201` only if separately selected.
Agent 3 must approve exact negotiation/DTO/error/status semantics before API work.
Operation polling is authoritative for execution; GenerationStatus is a scoped
source projection, not a second scheduler. Current v1/v2 remain synchronous and
unsaved. Phase A's proposed public session/CSRF/quota gate for legacy routes is
an explicit transport compatibility change requiring coordinated rollout, not a
change already approved or implemented by this document.

## Approval decisions and verification

1. Agent 3 review of operation states, public cancelled state, async negotiation,
   cancellation API and safe error/diagnostic exposure; no unilateral DTO changes.
2. Anonymous session lifetimes, verified claim handoff, quota counting/release and
   idempotency replay retention; distinguish replay from deliberate regeneration.
3. Durable dispatch/unknown-send recovery protocol, worker lease/clock policy and
   queue TTL. No exactly-once external generation/billing guarantee is possible.
4. Encrypted short-lived request/snapshot storage, access, deletion and retention
   across source, editable Book, backups and abandoned anonymous resources.
5. Retry coefficients and future long-book capacity classes/chunk evaluation;
   today's models, limits and budgets remain unchanged. Approve integration base
   and merge ownership separately before combining agents' branches.

Proposed joint offline acceptance: duplicate concurrent submissions; claim during
queued/processing/completion; old guest denied afterward; quota across UTC midnight;
crash before/after send and ambiguous completion commit; stale-worker fencing;
cancel/finalize races; no replay budget reset; source+Book rollback; lossless Hebrew
sentence-unit mapping; 27-page ordered targets; 32-page zero-call admission failure;
safe polling with no private draft or diagnostic leakage. Use fake providers and
synthetic data, plus Agent 3's opt-in database tests when implementation is approved.

Verification for this task is document/source inspection and Markdown checks only;
no new runtime or persistence behavior is claimed. No live AI calls, configuration
changes, shared code edits, merge, push or deployment. Wait for approval.
