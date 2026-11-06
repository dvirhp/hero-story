# Current long-book capacity and reliability

> Historical assessment at commit `86da2f2`. The approved 2026-11-06 whole-book
> implementation changes allocations, retry scheduling and the isolated runtime;
> see [current behavior and evaluation plan](WHOLE_BOOK_RELIABILITY.md). The tables
> below describe the former configuration, not current capacity. No new live
> generation evidence is claimed.

Status: **offline assessment and controlled-evaluation proposal only**. No live
provider call or runtime configuration change. Complements
[reliability design](AI_GENERATION_RELIABILITY_DESIGN.md) and
[B1 projection](PHASE_B1.md). Structural fit is not a demonstrated completion rate.

## Verified normalization capacity

Read the unchanged settings/PagePolicy and resolved profiles; exhaustively run
normalize_v2 for N=1..32, both languages, both densities, representative band
starts 0/3/12/36/72. Runtime JSON was parsed directly as RuntimeConfiguration;
no environment, credentials, SDK clients or configured app lifespan were accessed.
Tests' larger injected Fake settings are not production/live configuration.

The entries below mean every N from 1 through the listed maximum passed
normalization for the simple synthetic request used. They exclude actual prompt
input sizing, monetary/aggregate dispatch reservations, provider acceptance and
manuscript quality, which are checked separately. Structured targets or larger
personalization may cause later pre-dispatch rejection. These are not promises
that all books of those lengths are operationally supported.

| Runtime / language / density | Newborn | Infant | Toddler | Preschool | Older provisional |
| --- | ---: | ---: | ---: | ---: | ---: |
| Default Fake, English light | 10 | 10 | 10 | 10 | 10 |
| Default Fake, English standard | 10 | 10 | 10 | 10 | 10 |
| Default Fake, Hebrew light | 10 | 10 | 10 | 10 | 10 |
| Default Fake, Hebrew standard | 10 | 10 | 10 | 10 | 7 |
| Isolated Roy Gemini, English light | 29 | 29 | 29 | 29 | 29 |
| Isolated Roy Gemini, English standard | 29 | 29 | 29 | 29 | 29 |
| Isolated Roy Gemini, Hebrew light | 29 | 29 | 29 | 29 | 27 |
| Isolated Roy Gemini, Hebrew standard | 29 | 29 | 29 | 25 | 17 |

Ordinary Fake settings: Planner 1200, Writer 3000, input 8000, active deadline
90 s / attempt 30 s. Isolated `roy-alphabet-runtime.v2.proposed.json`: Planner
3000, Writer 6000, input 32000, global 3 attempts / 1 possible quality rewrite,
45 s/attempt, 135 s overall, 111000 token units, USD 0.075. The latter is an
isolated test configuration, not a new default. No live availability/pricing
reverification is claimed in this offline assessment.

PagePolicy allocation: P=200+96N; W=456+N*(40+ceil(density_max*language_ratio)),
with current ratios en=2, he=4. Default Planner fits N<=10; isolated Planner fits
N<=29. For N=32 P=3272>3000; N=27 P=2792. Writer sizing further limits Hebrew
preschool/older density as shown. Total costs/input reservations can reject more;
never lower requested N or density to avoid admission failure.

## Structural versus operational versus editorial limits

- B1 canonical safety ceilings: 128 entries, 400 code points/entry, 262144 bytes/
  document and 16777216 bytes/Book. Default product maximum 32 is configurable.
  These do not grant provider tokens, attempts, time or additional billable calls.
- Runtime ceilings: stage output/input capacities, model context/output
  declarations, aggregate tokens/USD reservations, deadlines and shared attempts.
  Normal workflow needs 2 calls, leaving at most one recovery slot under max 3.
- Editorial constraints: exact requested target structure and configured word
  density are deterministic; fluency, teaching, continuity and emotional quality
  require reviewed evaluation. Baby books do not need conventional conflict.

Offline Fake tests exercise exact 1/6/27/32-page books using explicit larger test
capacities. This proves structural paths only. No current evidence establishes
commercially reliable live generation at 27 or 32 pages. Worldwide language support
also remains future reviewed language packs; executable paths are he/en only.

## Failure evidence and uncertainty

| Observation / category | Evidence / interpretation |
| --- | --- |
| Provider availability | Prior approved 27-page Hebrew run: Planner success, two Writer upstream HTTP 503s, three total calls; no accepted story. Root cause unknown |
| Attempt exhaustion | Final BUDGET_EXCEEDED / attempt_capacity_exhausted describes no remaining call capacity; it does not establish spent USD ceiling |
| Short control | Prior approved 2-page English run: 200, two successful calls, gate passed, 4.62 s and estimated USD 0.0016875. One success does not isolate language/length/load/time |
| Invalid provider output | Mock/scripted malformed or out-of-density Writer outputs can exhaust recovery with PROVIDER_OUTPUT_INVALID attempt evidence; not an upstream 503 |
| Quality rejection | A schema/context-valid draft missing personalization can fail gate and return QUALITY_REJECTED after bounded repair; not provider transport failure |
| Preflight token capacity | 32 pages rejected under isolated Planner cap before paid work; no provider outage occurred in this arithmetic |
| Fake fixture defect | D-01 distribution issue fixed offline; not evidence of real-provider behavior or literary quality |

Use safe attempt category/status plus terminal stop reason in diagnosis. Unknown
provider usage retains conservative reservations; it is not zero. Do not infer
model overload, schema incompatibility, truncation, exhausted money or poor Hebrew
from the recorded 503s alone.

## Conservative path

1. Keep whole-book Writer as baseline, current four nodes and shared ledger.
   Preserve diagnostics, single-call SDK boundaries and terminal safety behavior.
2. Approve retry hardening separately: bounded jitter/backoff within existing
   deadlines/cost/call capacity, no hidden SDK retry or blanket repair prompt on
   transport failure. This assessment does not implement or authorize it.
3. Integrate B1 canonical admission only through Agent 3's approved application
   boundary; no provider-side or database side effects in projection itself.
4. Complete reviewed full-book educational/language rubrics and safe run artifacts.
   Separate provider errors from output-contract and editorial failures.
5. Seek a bounded matched live evaluation before claiming long-book reliability.
   If results justify chunking, first approve its global mandatory/recovery call
   budget, continuity and resume contract. Four chunks + Planner already needs
   five mandatory calls and cannot run under the current three-attempt limit.

## Candidate controlled evaluation: not authorized

Proposed first comparison: four independently approved synthetic requests, English
and Hebrew crossed with 2 and 27 pages, age 36/light, common adventure concept,
no educational targets, unchanged selected model/configuration. Review translated
concepts natively and randomize execution order; this reduces some confounding,
not all. Roy's educational case belongs to a subsequent separate approval; it
changes structural/teaching complexity and should not be conflated with plain
length. Additional repetitions are required before estimating reliable rates.

Each candidate request uses its normal allocation and existing 3-call / 45 s /
135 s / USD 0.075 caps. A four-request ceiling would be USD 0.300 internal budget
and at most 12 provider attempts, not a guarantee of invoiced cost; unknown usage
remains held. These totals are a proposal requiring explicit approval, not current
permission for any POST. Do not increase limits or run 32 pages while admission
rejects it. No automatic replacement POST, manual retry, model fallback or billing
change. If preflight cannot fit, stop rather than silently change the request.

Before execution approve exact requests/config hashes, current model/pricing
verification, privacy/retention and native review rubric. Capture sanitized
status/stage/attempt/stop reason, known/unknown tokens/cost and end-to-end latency;
save accepted complete manuscripts only under approved private evaluation handling.
Score exact structure, educational correctness when applicable, age fit, fluency,
coherence, character consistency, repetition and read-aloud experience. Stop each
run after its single POST and present failures without speculative root causes.
