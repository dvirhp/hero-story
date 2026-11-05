# Final AI/backend technical reconciliation

Status: **design decision record for final approval; no implementation authorized**.
Reviewed 2026-11-05. Exact inputs: Agent 1 integration contract `49410d0` and
Agent 3 Phase A `7e38326`, inspected through Git objects. This addendum leaves
both reviewed revisions intact. It specifies proposed resolutions; it does not
claim that Agent 3's shared DTOs or Phase A documents have already been edited.
See the [reviewed integration contract](AI_BACKEND_INTEGRATION_CONTRACT.md).

The user approved the seven operational defaults in principle. They must be
validated configuration, frozen per operation where applicable, and verified
offline. They are not new provider budgets or an availability guarantee.
Other numeric candidates (polling 2 s, cleanup 60 s, three finalization transactions
with 1/2 s waits, and canonical/HTTP size caps) still require final approval.

## Decision table

APPROVED means the design invariant is settled for final review, not implemented.
CHANGE REQUIRED means this record specifies a necessary correction to shared
documents/contracts. BLOCKED means a release dependency remains unresolved.

| Item | Decision | Resolution / dependency |
| --- | --- | --- |
| Separate v3 sync/async routes; one capability-scoped operation | APPROVED | Async is the primary frontend path; exact replay matrix below |
| Exact v3 DTOs and public error serialization | CHANGE REQUIRED | Adopt the field lists below in Agent 3's API design before shared code |
| Public cancelled state and cancellation races | APPROVED | Idempotent authorized command; completion/cancellation has one atomic winner |
| Anonymous issuance ownership and claim namespaces | APPROVED | Same immutable owner on operation/source/initial Book; no UUID-only access |
| Seven configurable operational defaults | APPROVED | Values approved in principle; validation/verification still required |
| Encrypted storage and deletion implementation | BLOCKED | Select key-management/backup-erasure mechanism and approve retained Book/source policy |
| Durable attempt/lease/finalization ports | CHANGE REQUIRED | Adopt the transaction semantics below; no independent second ledger |
| Canonical capacity admission | CHANGE REQUIRED | Versioned capacity profile and finite numeric candidates below need approval |
| Legacy payload/error compatibility | APPROVED | Preserve engine contracts; no silent conversion to durable work |
| Public legacy access/quota gate and frontend rollout | BLOCKED | Agent 2/4 coordination and integration approval required before public exposure |
| Automatic uncertain-send recovery/chunking | APPROVED | Disabled initially; neither is authorized by these defaults |
| Production activation | BLOCKED | Security, durability/race tests, privacy and explicit implementation/release approval |

## 1. Proposed exact v3 wire contracts

All objects forbid extra fields; scalars are strict JSON types. UUIDs are canonical
UUID strings; timestamps are RFC3339 UTC with Z; counts are strict integers >=0;
money/seconds are finite nonnegative JSON numbers. Nullable fields below are
required keys with null when absent. Messages come from a fixed server registry,
never exception text. No ORM objects or private engine snapshots are serialized.

Requests for both POST `/v3/books/ai` and POST `/v3/jobs/stories` are the unchanged
`StoryRequestV2` JSON contract: explicit page_count, he/en, strict age_months >=0,
no maximum age, optional explicit pronouns/ordered targets and existing defaults.
No wrapper, owner, provider/model, budget or transport selector is added to its
body. Session cookie, X-CSRF-Token and Idempotency-Key are required. Key syntax
is 22-128 base64url characters; frontend generates 256 random bits. Syntax cannot
prove entropy and a key never authenticates ownership.
Proposed configurable v3 generation-body cap: 256 KiB before JSON parsing; this
is a new transport-capacity candidate requiring approval, not a legacy limit edit.

### OperationStatus v1 (also the OperationAccepted body)

| Field | Type / exact rule |
| --- | --- |
| schema_version | Literal "1" |
| operation_id, generation_id | UUID; distinct stable operation and source IDs |
| capability | Literal "story_generation" |
| state | queued / processing / completed / failed / cancelled |
| phase | null / planning / writing / retry_wait / checking / finalizing |
| created_at, updated_at, queue_expires_at | UTC timestamps |
| started_at, execution_expires_at, finished_at | Nullable UTC timestamps |
| requested_page_count | Positive integer from frozen request |
| validated_page_count | Integer 0..requested_page_count; whole-book baseline reports 0 until complete gate acceptance |
| result | null or `{book_id:UUID}`; only completed; no pages or draft |
| error | null or OperationError below; only failed/cancelled |
| usage | null before dispatch, otherwise PublicUsageSummary below |

queued: phase/start/active expiry/finish/result/error null. processing: phase,
start and active expiry required, finish/result/error null. completed: finish,
result and full validated count required, phase/error null. failed/cancelled:
finish/error required, result/phase null. A cancelled-before-start job may have
null start/active expiry. Late accounting may update usage/updated_at but never
terminal state, finished_at, result or dispatch capacity.

OperationError is exactly `{code,message,retryable,stop_reason}`. retryable is
always false for terminal operations: no automatic fresh POST. code is an existing
GenerationError code, or QUEUE_EXPIRED / EXECUTION_OUTCOME_UNKNOWN /
PERSISTENCE_UNAVAILABLE / EXECUTION_VERSION_UNSUPPORTED. stop_reason is an existing
safe StopReason value or queue_expired / outcome_unknown / persistence_failure /
execution_version_unsupported. These additions belong to v3 API DTOs only, not
legacy engine enums. CANCELLED pairs with cancelled. An uncertain send uses
EXECUTION_OUTCOME_UNKNOWN/outcome_unknown, not PROVIDER_UNAVAILABLE or a claim
of monetary exhaustion. Engine failures retain their established code/reason.

PublicUsageSummary is exactly `{attempt_count,known_input_tokens,
known_output_tokens,known_estimated_cost_usd,upper_estimated_cost_usd,
has_unknown_usage,has_unknown_cost}`. It contains only aggregate numeric/boolean
values, not attempt arrays, stage models or upstream statuses. Known token totals
sum non-null reported/estimated attempt counts; they are partial if unknown usage
exists. Upper cost retains conservative holds; neither cost field is customer
billing. Unknown usage is never fabricated as a complete zero-cost result.

GET `/v3/operations/{operation_id}` returns 200 OperationStatus for all states.
Missing/foreign resources share 404. No-store applies to success and errors.
Use Retry-After: 2 for nonterminal polling initially (configurable), no polling
Retry-After on terminal responses. X-Request-ID describes the current HTTP request;
operation_id and generation_id remain stable across HTTP requests.

Queued response example (synthetic IDs; no child data):

```json
{
  "schema_version": "1",
  "operation_id": "10000000-0000-4000-8000-000000000001",
  "generation_id": "20000000-0000-4000-8000-000000000001",
  "capability": "story_generation",
  "state": "queued",
  "phase": null,
  "created_at": "2026-11-05T10:00:00Z",
  "updated_at": "2026-11-05T10:00:00Z",
  "queue_expires_at": "2026-11-05T10:05:00Z",
  "started_at": null,
  "execution_expires_at": null,
  "finished_at": null,
  "requested_page_count": 27,
  "validated_page_count": 0,
  "result": null,
  "error": null,
  "usage": null
}
```

### Synchronous success and common errors

AIBookCreated is exactly `{book:BookDetail,generation:GenerationReceipt}`.
BookDetail remains Agent 3 Phase A's canonical DTO including ordered PageDocuments;
no second StoryV2 page array is included. GenerationReceipt is
`{operation_id,generation_id,request_id,status,quality,usage,total_latency_seconds}`:
UUID IDs; request_id is the original engine correlation; status="completed";
quality=`{passed:true,check_version,rubric_version,advisory_count}`; usage is
PublicUsageSummary; latency is original engine duration, not replay latency.
Quality versions use existing bounded Label strings and advisory_count is >=0.
This replaces Phase A's still-unspecified SafeUsageSummary and full QualityReport
wire projection. It does not alter stored source quality or legacy responses.
On replay BookDetail is the current authorized Book revision, not a restoration
of the original generated content; source receipt remains labeled source metadata.

V3 ErrorEnvelope is exactly `{status:"failure",request_id,error,resource,execution}`:
error=`{code,message,retryable:false,stop_reason}`; resource=
`{operation_id:UUID|null,generation_id:UUID|null,book_id:UUID|null}`;
execution=`{generation_attempted:bool|null,save_outcome:null|"unknown"|"not_saved"}`.
Only report not_saved after established rollback, never after ambiguous commit.
For unauthorized/missing resources all resource IDs are null. No error reflects
submitted values, validation input, raw quality guidance or provider diagnostics.

Relevant fixed transport codes/statuses: existing engine codes retain their
synchronous HTTP mappings; 401 SESSION_REQUIRED; 403 CSRF_REJECTED or
CHALLENGE_REQUIRED; 404 NOT_FOUND; 413 REQUEST_TOO_LARGE; 422 INPUT_INVALID or
CANONICAL_CAPACITY_EXCEEDED; 428 PRECONDITION_REQUIRED for missing key; 429
DAILY_LIMIT_REACHED or ABUSE_THROTTLED; 503 ADMISSION_UNAVAILABLE or
PERSISTENCE_UNAVAILABLE; 409 IDEMPOTENCY_CONFLICT, IDEMPOTENCY_VERSION_UNSUPPORTED
or OPERATION_IN_PROGRESS; 410 RESULT_DELETED. Error messages are fixed; quota/reset
headers follow Phase A. Malformed keys are 422 INPUT_INVALID. No HTTP error code
authorizes client-side provider retries.

### Cross-route replay matrix

Authenticate, verify CSRF, bound/parse the body, then resolve the key within
story_generation across current authorized namespaces and retained digest-key
versions. Fingerprint stored-version canonical client input, excluding route.
Freeze all resolved server configuration separately. Replays bypass new quota/
capacity checks; access checks and existing-key verification still apply.

| Route / condition | Status and body / headers |
| --- | --- |
| Async new admission | 202 OperationStatus(queued), Location operation URL, Retry-After: 2 |
| Async matching key, any retained state | 200 current OperationStatus, same Location; polling delay only if nonterminal |
| Sync new, successful | 201 AIBookCreated, Location Book URL, Book ETag |
| Sync matching completed key | 200 AIBookCreated, same Book identity, current revision/ETag |
| Sync matching queued/processing key | 409 OPERATION_IN_PROGRESS, authorized operation Location; never attach another runner |
| Sync matching failed key | Original terminal safe error/status; unknown-outcome failure maps to 503, source errors retain their mappings |
| Sync matching cancelled key | 409 CANCELLED, stop_reason=cancelled; this is a v3 replay transport decision, not a legacy mapping change |
| Same key, different client request / ambiguous namespace collision | 409 IDEMPOTENCY_CONFLICT; no work |
| Existing key, unsupported canonicalizer | 409 IDEMPOTENCY_VERSION_UNSUPPORTED, authorized reference; no reinterpretation |
| Required retained verification key temporarily unavailable | 503 ADMISSION_UNAVAILABLE; no creation |
| Result erased within replay window | 410 RESULT_DELETED; minimal authorized tombstone, no restoration |

All POST replay responses add Idempotency-Replayed: true; new admissions use false.
No second daily unit, source record or provider call is created by replay. Original
sync/async execution semantics stay frozen; switching transport does not detach
a sync job. Retain verifier/canonicalizer support for the full replay window.
Expired keys lose deduplication guarantees; clients never retry them automatically.
Deleted-operation status lookup also returns 410 only within authorized retained
tombstone scope; inaccessible/nonexistent remains 404. No public deletion route
is introduced by this record.

## 2. Cancellation contract

POST `/v3/operations/{operation_id}/cancel`, body exactly `{}`, session and CSRF
required. No Idempotency-Key or Book If-Match is required: this is an inherently
idempotent operation command serialized by operation state/version. It is not
a Book edit. Authorized account scope includes claimed issuance namespaces.

| Current state | Atomic effect / 200 response |
| --- | --- |
| queued | cancelled; fail pending source/CANCELLED; release only never-authorized daily reservation; invalidate dispatch authority |
| processing | cancelled; fail source/CANCELLED; fence new authorizations/finalization, retain consumed unit/uncertain cost; signal local cancellation |
| cancelled | Same cancelled OperationStatus; no second release |
| completed | Completed OperationStatus with existing Book; no deletion |
| failed | Same failed OperationStatus; no reopening |

Use the same canonical-principal -> operation -> quota -> source -> Book lock
order as admission/finalization. State transition and ledger settlement commit
before reporting success; uncertain storage commit returns safe 503, client may
resolve by GET or repeat this cancellation command. Completion/cancellation race
has one winner. Cleanup is not allowed to publish after cancelled wins. An
already authorized provider request may still send/bill; no external recall
promise. Late safe usage reconciles without resurrecting content. Browser
disconnect, guest credential revocation and namespace claim never cancel async
work. Missing session is 401; foreign/missing operation is 404; CSRF failure 403.

## 3. Configurable retention and deletion

| Data / control | Settled default or proposed constraint |
| --- | --- |
| Queue TTL | 5 minutes from admission; no renewal |
| Worker lease / heartbeat | 60 seconds / 10 seconds; cannot renew an expired fence |
| Guest session | Idle 7 days / absolute 30 days; credential rotation never extends absolute expiry |
| Idempotency | Nonterminal lifetime + at least 48 hours terminal; minimum bounded tombstone if content erased |
| Accepted-result envelope | 15 minutes from first durable acceptance, never extended by retry |
| Normalized request/validated-plan envelope | Queued expiry is queue_expires_at; first processing replaces it with the once-set execution_expires_at; delete earlier on terminal outcome |
| Logical / physical cleanup | Deny access/use at expiry; proposed physical deletion within 60 seconds; retry cleanup and alert until deletion is confirmed |

Persist private envelopes separately from operation status/source pages, encrypted
with authenticated encryption through an injected reviewed crypto adapter. Bind
operation ID, immutable owner, envelope type/version, digest and expiry to integrity
checks; keys never appear in rows/logs. Accepted envelope contains complete validated
story, required frozen brief/constraints and quality/ledger evidence for lossless
finalization; it is the explicit exception to ordinary input expiry. No raw provider
responses, prompts or rejected drafts are retained. Only a current fenced worker
with that operation's authorization can decrypt; frontend cannot retrieve envelopes.

Completion/cancellation/expiry makes envelopes inaccessible transactionally; a
durable deletion intent removes ciphertext within the cleanup target. Cleanup
is idempotent and fenced against finalization; erase all temporary copies. Backups
must exclude these short-lived ciphertexts or provide equivalent bounded crypto
erasure; row deletion alone cannot establish this. Crypto/key infrastructure,
replica/backup disposal verification and durable Book/source retention are release
blockers, not silently selected here. Retain non-content budget/dedup evidence;
never delete quota history to grant new work. Session expiry is not data erasure.

## 4. Durable execution ports and invariants

Backend-owned ports are SDK/ORM independent. Inputs/outputs below are typed,
versioned, immutable contracts, with fixed errors (NotAuthorized, Conflict,
Expired, CapacityRejected, StorageUnavailable), no free-form exception fields.

| Port operation | Required atomic semantics |
| --- | --- |
| admit(access, key, request, policy_snapshot) -> NewOperation or Replay | Resolve canonical scope, replay or reserve daily unit/source/operation/frozen snapshot together; fail closed |
| claim(operation_id, worker_id) -> ExecutionLease | Conditional queued -> processing, start source and active expiration once; monotonically increasing fence; backend clock |
| heartbeat(lease) -> renewed lease | Current unexpired fence only, bounded lease duration; never move active expiration |
| reserve_attempt(lease, stage, slot, reservation, payload_digest) -> DispatchPermit | Check state/cancel/deadline, global <=3 calls, token/USD and mandatory future work; persist reservation and consume first daily unit coherently before network |
| record_outcome(permit, safe_outcome, validated_snapshot_ref) | Idempotent same attempt/outcome; reject conflicts; store allowlisted usage/diagnostics; failed usage can remain unknown |
| stage_accepted(lease, accepted_result, frozen_context) -> envelope_ref | Validate full gate/canonical projection, ownership and timely acceptance; encrypt durably with original expiry and record finalization phase |
| finalize(lease, envelope_ref) -> BookRef | Verify unexpired envelope/fence/cancellation; source completion + unique initial Book/pages + operation completion in one UoW |
| cancel(access, operation_id) -> OperationStatus | State-winner rules above; coherent fencing/quota settlement |
| recover(operation_id) -> safe decision | Authoritative lookup only: known completed, permitted queued claim, eligible finalization, or conservative terminal failure; never resend uncertain provider attempt |
| expire_and_cleanup(reference, expected_version) | No provider call; fail/settle/fence as needed, then idempotent encrypted payload deletion |

DispatchPermit contains operation/attempt UUIDs, global slot, fence, stage,
expires_at, input/output/cost reservation, payload digest and frozen policy
reference. It is server-internal, never a bearer credential exposed to clients.
Persist an attempt in authorized/started/outcome-recorded/unknown accounting
states; a missing response is not a zero-cost failure. Unique(operation,slot)
and conditional updates reject duplicate authorization and conflicting callbacks.
Do not use float equality as monetary admission authority: the port must use
fixed-precision monetary units with explicit conservative rounding; public
estimated JSON amounts are projections only.
ExecutionLease contains operation_id, worker_id, strictly increasing fence,
lease_expires_at and original execution_expires_at. Workers are authenticated
internal actors, not arbitrary caller IDs. record_outcome is keyed by immutable
attempt identity; it cannot allocate another slot. Automatic recovery prohibition
applies to missing/ambiguous durable send outcomes; a durably recorded adapter
failure follows only the approved classified engine retry policy, retaining
conservative unknown-usage holds. No worker redelivery adds another retry layer.

Engine owns the graph and budget math; the durable journal is the one authority.
A durable runner must integrate these ports before provider I/O; calling today's
fresh StoryEngine.generate after redelivery does not implement recovery. Legacy
request-local execution remains unchanged. No transaction spans provider I/O.
Lost leases fence future writes/publication but cannot recall committed send
authorization. Late trusted usage reconciliation may append accounting for a
terminal/stale attempt under a restricted service port, without accepting drafts
or renewing its right to publish.

Initial recovery: zero uncertain provider resends; no automatic interrupted
processing resume. Proven never-processed queued work can be claimed before queue
expiry. Finalization recovery alone may reacquire a new fence for
processing/finalizing after lease expiry, without changing acceptance/active/
envelope expiration. At most three storage transaction attempts total, including
original, waits 1 s then 2 s; persist count across crashes. Reconcile ambiguous
commits before spending another transaction attempt. Outcome still uncertain:
no new publication attempt until authoritative storage can resolve it. Timely
accepted envelopes can finalize after the AI deadline but never after their own
15-minute window; no new provider dispatch. Persisting acceptance must verify all
provider attempts needed for that result have recorded successful validated outcomes.

Restricted diagnostics allowlist: fixed category, nullable upstream HTTP status,
existing fixed code/stop reason and attempt/latency/usage/reservation/version fields.
No exception strings/headers/URLs/prompts/content. Approving this restricted port
does not expose those fields through v3 DTOs or expand legacy logs. Existing SDK
single-call behavior and all runtime limits remain unchanged. Retry coefficients
from the reliability proposal are still a separate implementation approval point.

## 5. Canonical capacity policy: numeric candidate for approval

Define versioned configurable `ai-text-document-v1`, distinct from template/manual
limits. Initial candidate: max 32 story pages, title <=120 code points; each page
exactly one text block, text-only-v1/body, <=128 nonempty sentence units, each
<=400 code points; compact UTF-8 serialized PageDocument <=256 KiB; aggregate
canonical Book response <=16 MiB. These **new capacity values require approval**;
they do not change today's engine schema, page policy or provider allocations.
The effective page range is the intersection of service and canonical limits;
no clamping. Age does not select N or impose an upper age cutoff.

Verified existing bounds: Label <=120, ShortText <=400, every sentence unit has
non-whitespace content. Therefore units per accepted page <= its hard word maximum
W; optional requested unit range can tighten that bound. Current largest profile
W=70 gives <=28,000 text code points/page. Conservatively allow six encoded JSON
bytes per code point plus quotes/commas and exact bounded wrapper/IDs. Use the
actual configured canonical serializer (UTF-8, ensure_ascii=False, fixed compact
separators); reject lone surrogates/unsafe controls. Do not estimate from tokens.

Admission computes finite U=min(W, requested unit maximum when supplied), verifies
U<=128 and max unit length<=400, counts one block and bounds serialized page plus
all N page/Book wrappers. Require exact calculated upper bounds below both byte
caps. If any profile/config field is unbounded or representation cannot be proven
to fit, reject before quota consumption/dispatch; never reduce requested density,
unit range or N. Repeat exact serialization/shape validation after acceptance.
Direction/Unicode logical order, source IDs/targets and unit order are preserved.

The bound does not make 32 pages executable: unchanged isolated Planner cap 3,000
still rejects its 3,272-token estimate; 27 pages needs 2,792. No broader 32-page
promise, token limit increase or chunked execution is authorized.

## 6. Legacy compatibility and frontend migration

Keep existing v1 deprecated and synchronous, v2 synchronous/unsaved, their strict
domain payloads, success/failure enums/status mappings, and disconnect cleanup.
Do not add Book DTOs, mandatory page_count to v1, or asynchronous detachment.
Legacy HTTP body compatibility does not mean access behavior stays identical in
a future public deployment: Phase A's session/CSRF/quota gate adds documented
401/403/429/503 behavior. Proposed pre-engine gate-unavailable mapping is
503 CONFIGURATION_ERROR with a fixed safe message/empty usage, plus
explicit admission reason header; never dispatch on unknown quota state. Other
legacy gate mappings/headers remain Phase A's proposal. This mapping requires
Agent 3/4 confirmation; no new legacy domain code is introduced. This is a
gate-specific HTTP mapping: an engine CONFIGURATION_ERROR retains its existing
500 behavior. Do not claim the new public gate is transport-identical to old v2.

Frontend migration: bootstrap same-origin session, credentials included, CSRF
only in memory, keep one random key per deliberate creation and explicit bounded
transport recovery. Use async submission -> authorized polling -> BookDetail;
no automatic new-key retry, no submission from polling/render effects. Detect
session loss instead of silently issuing a fresh paid creation. Clear private
memory on session/account changes. Never put child payloads/tokens in URLs or
localStorage. BookDocument reader is separate from existing v2 StoryReader;
Book edits use ETag/If-Match. Present source quality as source-only, stop reasons
as distinct from monetary failure, daily allowance as attempts, and cancellation
as possibly billable after dispatch. No book text in status polling/telemetry.

Public rollout requires all publicly reachable AI routes to share access/abuse/
quota controls, or keep legacy routes unreachable publicly; never leave a bypass.
No frontend, route, database or integration branch change is performed here.

## First independently implementable Phase B slice

Critical design gaps are now explicit, but storage/security deployment invariants
are not yet verified. Recommend **Phase B1: pure canonical AI projection and
capacity contracts**, after approval of the numeric profile. No queue, route,
provider call, database migration, claim/auth implementation or durable worker.
Agent 3 owns PageDocument/Book projection contracts; Agent 1 supplies existing
accepted-result/brief interfaces. Preserve current v1/v2 behavior.

Acceptance tests (offline): strict extra/type/Unicode limits; all five age bands
in he/en with explicit N; age zero/open-ended ages; exact Roy 27-target ordering;
lossless sentence-unit and source-ID mapping; canonical capacity boundaries and
configuration changes; 32-page unchanged Planner admission rejection; byte-bound
proof versus actual serialization including four-byte characters/escaped text;
no truncation/normalization; reject failed/incomplete/forged acceptance; owner
linkage mismatch; source quality never certifies edits; zero provider/network
calls and no shared legacy API changes. Database/lease/quota tests belong to later
approved slices, not fictitious coverage of these pure tests.

Remaining blockers: final user approval of DTO/error/capacity proposals; Agent 3
shared-document adoption; crypto/key/backup-erasure and durable data retention
selection; transaction/fencing/cancellation race implementation and PostgreSQL
verification; frontend/legacy gate migration and integration ownership. Design
review does not certify that these invariants already hold in executable code.

Verification for this design-only review: exact commit documents inspected;
one queued-response JSON example parsed; current profile maximum W=70 checked;
representative ASCII/Hebrew/four-byte/escaped serialization sizes checked against
candidate page/Book byte caps. These samples are not a complete admission proof
or executable DTO validation. UTF-8, local links, balanced fences and whitespace
checks passed. No application tests, database changes or provider calls performed.
