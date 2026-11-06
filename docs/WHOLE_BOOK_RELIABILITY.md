# Whole-book reliability implementation

Approved scope, implemented offline on 2026-11-06. One global Planner, one
whole-book Writer, the existing deterministic Quality Gate and unchanged B1
projection remain the architecture. No chunking, checkpointing, persistence,
additional graph nodes, paid calls, deployment or provider fallback is added.

## Recovery and compatibility

The three-attempt shared ledger and maximum one quality rewrite remain intact.
Every dispatch reserves its full input/output allowance and stage-priced cost
before I/O. Unknown usage retains reservations. Framework and SDK retries remain
disabled. Failed drafts never become accepted engine results or projected Books.

| Failure | Recovery |
| --- | --- |
| Retryable 503/service failure, connection failure, attempt timeout | Same semantic payload; bounded jittered backoff; no schema-recovery instruction |
| Malformed JSON, schema or contextual violation | Existing bounded static schema-recovery instruction; no transport backoff |
| Gemini MAX_TOKENS/CONTINUATION or OpenAI incomplete/max_output_tokens | `output_truncated` attempt diagnostic; replay within remaining capacity, unchanged output allocation, no schema-recovery claim or automatic continuation |
| Valid draft failing deterministic quality | Existing sanitized repair issues and whole-book rewrite, sharing the same third slot |
| Unsafe output, refusal, permanent configuration failure | Terminal; no repair |

Public error codes and HTTP mappings are unchanged. Truncation retains
`PROVIDER_OUTPUT_INVALID`; the allowlisted diagnostic category distinguishes it.
OpenAI HTTP failures now preserve status/category just as Gemini does. Both
providers preserve Retry-After on HTTP timeout responses as well as availability
responses. An exhausted transient retry can still end as `BUDGET_EXCEEDED` with
`attempt_capacity_exhausted`; the attempt ledger preserves the upstream cause.

`AppSettings.retry` is a strict versioned `RetrySettings` value. Defaults:

```text
ceiling = min(8 seconds, 1 second * 2**(consecutive_transient_failures - 1))
jittered = ceiling * (0.5 + 0.5 * injected_random_value)
delay = max(valid_provider_retry_after, jittered)
```

Provider delays are not shortened to the eight-second jitter cap. Check attempt,
input, token and cost capacity before waiting. Delay plus a minimum useful call
allowance for remaining mandatory calls must fit the overall deadline; recheck
time after waiting. Cancellation while waiting preserves the completed ledger
without creating an undispatched attempt. Inject clock/sleep/randomness for
deterministic tests. As with existing synthetic provider latency, an injected
sleep/clock that does not advance still consumes the requested wait in virtual
elapsed time. No deadline is extended.

## Offline capacity calibration

`page-policy-v2-2` explicitly budgets JSON metadata, visible-output headroom and
thinking. These are provisional engineering estimates, not measured Gemini or
OpenAI tokenization or demonstrated completion rates. Natural prose, unusually
long identifiers, larger plans or many sentence entries may require more space;
the full prompt/schema bound and output validation remain mandatory.

```text
P = 256 + 112*N + 256
visible_W = 256 + N*(64 + ceil(max_words_per_page * language_ratio))
W = ceil(1.25 * visible_W) + 1024
language_ratio: en=2, he=4
```

The Planner includes a separate 256-token thinking allowance. Writer headroom is
25% above the visible estimate plus 1,024 thinking tokens. The same allocation
snapshot drives the actual dispatched max_output_tokens, known-usage checks,
normalization, mandatory-future-call admission, aggregate tokens and stage-priced
cost reservations. Increasing a runtime ceiling alone never changes allocation.

For Roy: P=3,536 and W=6,744 (previously 2,792/4,128).
For 32 pages: P=4,096. Writer allocations across all current profile bands:

| Band | English light | English standard | Hebrew light | Hebrew standard |
| --- | ---: | ---: | ---: | ---: |
| Newborn | 4704 | 5104 | 5504 | 6304 |
| Infant | 4864 | 5504 | 5824 | 7104 |
| Toddler | 5344 | 6304 | 6784 | 8704 |
| Preschool | 5824 | 7504 | 7744 | 11104 |
| Older/open-ended | 7104 | 9504 | 10304 | 15104 |

The isolated `roy-alphabet-runtime.v2.proposed.json` now provides Planner/Writer
ceilings 6,144/16,384, 32,000 input, 140,000 aggregate units, USD 0.15, three
attempts, 45 seconds/attempt and 150 seconds overall. It remains an evaluation
configuration requiring explicit opt-in and live-run approval, not a production
default or permission to call a provider. Default Fake settings and legacy v1
stage allocations remain unchanged. Older custom runtime ceilings can now reject
more v2 requests because the allocation is more conservative; never clamp N or
reduce density to compensate.

At the file's historical declared rates ($0.30/M input, $2.50/M output), the
full-input-bound three-call reservation is 113,024 units / $0.07136 for Roy.
The largest current 32-page case is 130,304 units / $0.11456. Tests also check the
two-Planner/one-Writer branch. These are internal reservation calculations, not
current tariff verification or invoice guarantees. The new request deadline
leaves room above three 45-second attempts for local processing and backoff;
long Retry-After delays can still terminate safely.

## Explicit model thinking

Server-owned model capability records can specify `gemini_thinking_level` or
`openai_reasoning_effort`. The adapter serializes only the selected provider's
setting. The engine rejects a capability record carrying the other provider's
setting. No model-name guessing or unsupported reasoning parameter is sent by
default; `None` preserves older runtime behavior. A non-null setting is a
server assertion that it has been reviewed for that exact model, not automatic
model discovery. The Roy evaluation configuration selects Gemini `minimal` and
suppresses thought text. Output limits include thinking and all usage accounting
continues to include it. The old default model behavior is not silently changed
for other configurations.

Sources reviewed: [Gemini model specification](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite),
[thinking limits](https://ai.google.dev/gemini-api/docs/thinking#token-limits),
[retry guidance](https://ai.google.dev/gemini-api/docs/troubleshooting#retry-strategy),
and [OpenAI reasoning/output limits](https://developers.openai.com/api/docs/guides/reasoning).

## Offline evidence and limits

`tests/test_whole_book_reliability.py` exercises Roy's exact assignments and
personalization; 32-page Hebrew/English generation at upper density bounds across
all age bands and both densities; transport/schema/truncation/quality separation;
retry exhaustion, provider delay, virtual deadlines, cancellation during sleep,
budget-before-wait, and complete failure without an accepted story. Adapter tests
exercise real SDK serialization with mock transports, including thinking settings
and distinct truncation diagnostics. Existing B1 tests retain exact Unicode,
capacity, ownership, correlation and source-mapping coverage. Pytest blocks
network sockets; no credentials or raw live artifacts are needed.

Synthetic text demonstrates contract enforcement, not fluency, educational truth,
character/narrative consistency, safety beyond the current checks, provider
availability or latency. The prior Planner-success/two-Writer-503 observation is
still provider failure evidence, not proof that the manuscript is too long.

Final offline verification on 2026-11-06:

```text
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider
1055 passed in 220.87s (0:03:40)
```

The repository's `--disable-socket` pytest option remained active. `git diff
--check` also passed. No dependency/lockfile changes or live/provider probes were
required. The first full run found one new test expecting a different SDK wire
spelling for thinking configuration; correcting that expectation to the locked
SDK's actual field names/enum was verified in the final complete run.

## Proposed controlled live evaluation — NOT authorized

Before any run, approve frozen request/config hashes, exact model and current
prices/quotas, native review rubric, safe artifact retention and the aggregate
run budget. Recheck model support for the selected thinking level. Use synthetic
personalization only. No account or billing changes are part of the proposal.

First batch: four matched synthetic educational requests (Hebrew/English crossed
with 27/32 pages), plus Roy's existing 27-page Hebrew fixture as a separate fifth
case. Review a 32-target concept list in both languages; the matched 27-page cases
use its first 27 targets, with the same theme, preschool/light density and input
complexity. Roy remains a distinct alphabet/teaching case, not a length control.
A 32-page case must have 32 distinct requested targets, not five padded Hebrew
letters or a changed alphabet definition. Freeze cases and randomize order. One
POST each: at most 15 total attempts and USD 0.75 internal reservation ceiling
across five requests. No manual
replacement POST or automatic fallback. An outage does not authorize another run.

Capture only sanitized stage/cause/stop reason, completion versus truncation,
reported/unknown input/output/thinking tokens, reservations/cost and end-to-end
latency. Retain complete accepted manuscripts privately only under the approved
artifact policy. Require exact count, IDs/order, targets, personalization and
existing gate acceptance; review every page natively for fluency, teaching,
continuity, agency, repetition and read-aloud quality. Report transport failure
separately from output-contract and editorial failure. Five runs are an initial
screen, not a statistical reliability estimate. Repetitions and any high-density
32-page evaluation require their own approved ceiling and release thresholds.

Chunking remains excluded. Reconsider it only after repeated, classified live
evidence establishes a whole-book failure that simpler capacity/retry changes
cannot resolve.
