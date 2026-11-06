# Agent 3 handoff: synchronous frozen execution

2026-11-06. One local scoped integration commit approved on feature/whole-book-reliability.
Parent revision: 7a9d252d34026902d7d50606d3fb09f2d1d5fa6d. The commit containing this document
is the frozen synchronous execution baseline; obtain its exact SHA with git log/rev-parse rather
than treating the parent as the implemented interface. No merge/push/deployment or backend activation.
All unrelated dirty working-copy files and partially staged file contents are preserved.

Review fingerprints (SHA256 UTF-8 with LF line endings, not Git commits): engine.py
`3181b42460b0ff80906d86a79ca6bc7744d12ccd6bb3a1addbf8b430a9145428`;
synchronous.py `d2e1841bd77aa58d295d0d35258db05162d41cfe17a930315d762d3c20ed5713`;
synthetic fixture `1d5586aaed1a7e4a1d5006d14e1c4eeb327c560a59ccf74d65e91486b22bd31e`.

## Exact imports and call

```python
from storyforge.orchestration.engine import StoryEngine
from storyforge.orchestration.synchronous import (
    FrozenEngineManifestV1, SynchronousExecutionHooks, AttemptProposal,
    AuthorizationDecision, SendAuthorization, AttemptOutcome,
    ExecutionBoundaryStopped, FrozenExecutionInvalid,
)

# Trusted server composition, existing issued NormalizedBriefV2 and identities.
manifest = engine.freeze_manifest()
result = await engine.generate_frozen(
    brief,
    operation_id=issuance.issuance_id,
    request_id=issuance.request_id,
    manifest=manifest,
    execution_expires_at=original_utc_deadline,
    hooks=backend_hooks,
    cancelled=lambda: request_cancelled,
)
```

Returns existing GenerationSuccessV2 | GenerationFailure. Invalid input/configuration raises fixed
FrozenExecutionInvalid before provider calls. Existing generate(...) keeps legacy behavior and is
NOT a replay/recovery mechanism. Engine never accepts owner authority or saves canonical Books.

Frozen brief is strict JSON-revalidated and used EXACTLY, without normalization/profile resolution.
Manifest must match configured engine, supported profile/page/rubric versions, page range and output
caps. Existing actual capacity/budget checks still run. Config drift around hook waits prevents sends/
acceptance. Planner, Writer v2-3, Quality Gate and shared four-node graph remain the execution path.

## Manifest and reproducible vectors

FrozenEngineManifestV1 contains typed settings/limits/rules/page policy, stage pricing/capabilities,
profile/prompt versions, plan/story schema digests and token-bound algorithm. Fixed labels:
sync-engine-manifest-v1, sync-engine-v1, normalize-v2-frozen-v1, contract_version=2. Deployment additionally
pins approved package/commit; no Git/credential lookup at runtime. No secrets or endpoint overrides.

`manifest.digest()`: SHA256 of model_dump(mode="json"), sorted keys, UTF-8 ensure_ascii=False,
compact separators, allow_nan=False. Unkeyed hashes are for config/schema, NEVER private input.
Golden manifest/accepted/rejected/unknown-usage JSON: tests/fixtures/synchronous_execution_v1.json,
synthetic FakeProvider only. Manifest digest:
`cdd83148df570a7a4734eb69e84d0cfab08b90bf5c7eee293145e57146ecb6ff`.
Canonicalization vector: {"a":1} ->
`015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862`.

## Two required backend hooks

`authorize_attempt(proposal: AttemptProposal) -> SendAuthorization` runs AFTER retry waits and current
budget/deadline/cancel checks, BEFORE every adapter call. Proposal includes operation/request IDs,
slot/stage/provider, manifest/schema digests, token bound/output cap/reservation and mandatory future
slots/tokens/cost. Stable IDs: UUID5(operation_id,"sync-attempt:<slot>") and
UUID5(operation_id,"sync-authorization:<slot>"). These are correlations, not credentials; global slots 1..3.

`proposal.request` is exact LLMRequest, repr-hidden/serialization-EXCLUDED, transient in-process only.
Backend computes keyed semantic-input HMAC using that attribute; omit decreasing remaining_seconds,
bind expiry separately. Do not log/store raw instructions/input/rejected repair prose. Model/prompt/cap
are in LLMRequest; prices/capabilities in manifest. Nanos = ceil(Decimal(str(existing reserved USD))*1e9):
0.075 ->75000000; 0.0000000001 ->1; 0 ->0. No budget increase. Agree fixed-unit cap conversion before
production; legacy display floats are not new billing authority. Existing usage may increase holds.

Backend atomically enforces execution-once and unique operation/slot, reserves token/cost and consumes
original-day daily creation on FIRST authorization, then COMMITs before returning. Return
SendAuthorization(AuthorizationDecision(operation_id,request_id,attempt_id,attempt_number,stage,
manifest_digest,payload_digest,expires_at,disposition)), using named arguments. payload_digest is 64
lowercase hex; expiry aware UTC <= original active expiry; disposition NEW|REPLAY. Correlations/expiry
are validated. NEW is locally single-use; REPLAY/reused object/mismatched/expired receipt sends zero calls.
Durable cross-process uniqueness remains backend responsibility; a malicious hook minting fresh NEW
objects cannot be corrected by an engine-local lock. No permissive default hook exists.

Lost authorization acknowledgement raises AUTHORIZATION_UNCERTAIN; local invocation does not send.
The backend may already have committed, so reconcile rows and never regrant on lookup/retry. Local
safe_usage includes provisional conservative slots even on replay/ack loss: do not overwrite committed
accounting from it. Committed authorization cannot be refunded just because a send is unproven.

`record_outcome(outcome: AttemptOutcome) -> None` runs after schema/safety/context/accounting checks,
BEFORE another attempt or terminal return. Same identities/slot, RECORDED|UNKNOWN and safe AttemptRecord;
backend derives integrity digest and commits idempotently, rejects conflicting outcome. Explicit bounded
validation_issues (max8 fixed code/path/count) and truncated flag are internal-only, never raw prose.
No next call if acknowledgement fails. No separate sent flag or five separate callbacks required.

Known recorded failures follow existing bounded retry policy. Raised timeout/connection/unknown
exception and adapter timeout/cancel are uncertain; never automatically retry them. Unavailable without
known HTTP response is conservative uncertainty; known failed HTTP response with status can follow
recorded policy. UNKNOWN retains holds and actual known accounting if available; missing usage stays
unknown, not zero. During task cancellation, authorized slot stays unresolved; no detached recorder.

## Results and typed stop

Accepted: original request_id, complete ordered StoryV2, full usage/latency/resolved_constraints,
quality.passed=true, EXACT quality-v2+book-v2-1 / language-v1. Rejected: existing failure envelope,
safe error/stop_reason, usage and optional quality, NO story/draft. Supporting outcomes acknowledged.
Final return supplies success/rejection hook; B1 projection/quality reassessment and DB save are backend's.

ExecutionBoundaryStopped attributes: reason, operation_id, request_id, attempt_id|None, safe_usage.
Reasons: AUTHORIZATION_UNCERTAIN, OUTCOME_UNCERTAIN, STORAGE_UNAVAILABLE, CANCELLED. Fixed exception
string, no raw cause/task notes in exposed boundary. Reconcile backend records; never turn ambiguous
commit into proved rollback or call engine again automatically. Outcome-write retry is storage-only,
same identity/payload, never another authorization/provider call. Existing legacy error enums unchanged.

Injected `StoryEngine(..., utc_clock=...)` bounds active duration by original once-set UTC deadline AND
configured request timeout. Monotonic budget counts hook/wait/call duration; no deadline reset. Expired
initial deadline returns known zero-call deadline failure. UI 30–60 seconds is not a budget/SLA increase.
Cancellation checks around hooks/waits/calls/final return stop future sends; authorized work may bill.
No background tasks, worker, queue, lease, scheduler, persistence or automatic resume is implemented.

## Compatibility / remaining backend work

1. Pre-existing working-copy ProviderDiagnostic.validation_issues remain EXCLUDED from production JSON;
   hook exposes bounded metadata explicitly. Retention defaults/tooling unchanged. Never enable rejected
   manuscript retention for API generation merely to pass this interface.
2. Backend review confirmed output_truncated is ALREADY present in its pinned strict diagnostic enum
   and private metadata round trip. No enum/database extension is needed for that category alone.
   Bounded validation details remain hook-only; do not silently widen public result diagnostics.
3. Backend needs durable execution-once CAS, hook journal/first quota consumption, synchronous status/
   reconnect and owner-rechecked atomic source/Book/pages completion. Existing 0005 guards remain intact.
   No HTTP generation activation or PostgreSQL integration is delivered by this engine-only work.
4. Input encryption/retention remains a separate decision. Engine stores nothing; it does not satisfy or
   weaken backend mandatory sealing. Commit ambiguity/result loss -> lookup, not paid regeneration.

## Scoped commit contents and verification

The commit contains nine runtime source files: domain/{diagnostics,output_validation,story,story_v2}.py,
llm/fake.py, orchestration/{engine,synchronous}.py, prompts/v2.py, validation/output_diagnostics.py;
tests/{test_contracts,test_synchronous_execution,test_output_validation_diagnostics,test_roy_final_forms,
test_writer_word_limit_instructions}.py; tests/fixtures/synchronous_execution_v1.json;
and docs/{ORCHESTRATION,SYNCHRONOUS_EXECUTION_HANDOFF}.md.

Only core diagnostic tests are staged from test_output_validation_diagnostics.py. SDK-only test hunks
and OpenAI/Gemini diagnostic adapter edits remain unstaged; they are not required to execute this
interface. Evaluation tools/tests/results/manifests/manuscripts and ongoing quality recalibration are
excluded. No credentials, archives, caches, local configuration or other generated artifacts are included.
The JSON vector is deterministic synthetic FakeProvider contract data, not a live evaluation artifact.

Mixed files are staged as index-only source hunks matching the reviewed pre-recalibration fingerprints;
working-tree files are not overwritten. The read-only earlier build is a source reference only: no
wheel/archive is committed or required at runtime. The staged snapshot is exported and tested with
its own src on PYTHONPATH so unrelated dirty modules cannot mask missing commit dependencies.

Prior full dirty-worktree results (historical, not proof of this commit): 1,254 offline tests and
168 Python 3.12 engine/v2/interface tests passed. Final index-snapshot verification: **1,183 passed in 269.48s**, no failures/skips.
The 29 interface cases cover original identities, frozen snapshot/no normalization, NEW/REPLAY receipts,
retries/outcome acknowledgement, rejection, uncertainty, cancellation, config drift and Hebrew ordering.
No PostgreSQL, paid provider, worker or complete backend HTTP integration is claimed.

No paid evaluations repeated; real consumed guards and retained manuscripts are untouched. Exactly one
local commit is authorized; no merge, cherry-pick, push, deployment or backend work is performed.

Verification was run BEFORE commit on a materialized copy of the complete index, with PYTHONPATH
pointing exclusively at that export's src. Import-path assertion confirmed the engine came from the
export, not the live dirty worktree. Command: python -m pytest -q --tb=short (sockets disabled by project
configuration). All nine runtime source blobs, five test modules, synthetic JSON vector and two docs
were explicitly reviewed/staged; no unrelated quality-model source, SDK changes or evaluation files.
Secret-pattern/forbidden-path checks and git diff --cached --check passed. The source/test index was
unchanged during the run; only this verification note was subsequently added to the staged document.
