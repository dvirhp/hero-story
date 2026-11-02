# Explicit page count: implemented v2 contract

This approved Milestone 6 follow-up adds user-controlled book length. It does not
start Milestone 7 or authorize a live request. The original newborn smoke request
and its runtime file are unchanged. The user reports that earlier live test
succeeded; no further live call was made during this implementation.

## Request and migration

`POST /v2/stories/generate` requires a strict positive integer `page_count`.
Missing, null, boolean, fractional, string and `"auto"` values fail. The default
service policy admits 1–32 pages; both bounds are configurable in `PagePolicy`.
The service rejects an unsupported count rather than rounding, clamping or
silently changing it. Automatic length selection is reserved for a future
versioned request mode; it is not implemented.

`/v1/stories/generate` remains temporarily available and is marked deprecated in
OpenAPI. Its original schemas, profile data, age-derived lengths and response
shape remain isolated and unchanged. No removal date or automatic migration is
assumed. V1 rejects v2 fields rather than ignoring them.

Minimal v2 request:

```json
{
  "schema_version": "2",
  "language": "en",
  "display_name": "Or",
  "age_months": 0,
  "theme": "Gentle moonlight",
  "page_count": 4,
  "story_type": "bedtime",
  "text_density": "light"
}
```

V2 inherits existing strict age, language, name and explicit pronoun rules. Age
zero and an open-ended older-child band remain supported. Only `he` and `en`
execute today. No gender inference, translation fallback or new provider is added.

New optional fields are `story_type` (`general`, `bedtime`, `adventure`,
`educational`, `alphabet`), `text_density` (`standard` default, or `light`),
`requested_title`, and `structure`. Story types guide prompts through the same
graph; an alphabet adventure uses `alphabet` plus adventure guidance.

Breaking changes for clients migrating to v2:

- Supply `page_count` explicitly; do not copy a profile's old default implicitly.
- Accepted stories have `schema_version: "2"` and an explicit `page_count`.
- Each page has `page_id`, `page_number`, nullable `target_id`, and a nonempty
  `sentence_units` array. There is no separate `text` field: join units with one
  space to render body text. Python exposes a derived `.text` property.
- Success includes `resolved_constraints` with density, total-word range,
  ordered target IDs, sentence-unit bounds and policy version. Error envelopes,
  request IDs, usage accounting and HTTP status semantics are unchanged.
- Profile identifiers remain stable; the new configuration version is
  `development-v2-1`. Planner/Writer prompts are `planner-v2-1`/`writer-v2-1`.
  Quality reports use the injected rule version plus `+book-v2-1`.

Sentence units represent requested sentences or baby utterances. Counting entries
is deterministic; it cannot prove each entry contains exactly one grammatical
sentence. Sentence word length remains a soft developmental observation.

## Developmental data and normalization

`development/profiles.v2.json` contains five provisional age bands. It contains
no page counts or total-book lengths. The pure resolver returns an immutable
language-specific snapshot; normalization combines the requested pages with the
selected density to produce `BookConstraints`. Total words are always pages
times the per-page range, excluding the title. Word counts use whitespace.

| Profile | Months, lower inclusive | Light words/page | Standard words/page |
| --- | --- | --- | --- |
| Newborn | 0–3 | 5–10 | 5–15 |
| Infant | 3–12 | 5–12 | 10–20 |
| Toddler | 12–36 | 8–18 | 15–30 |
| Preschool | 36–72 | 12–24 | 25–45 |
| Older child, provisional | 72 onward | 20–40 | 40–70 |

These Hebrew/English starting values are product hypotheses requiring read-aloud
and native-language evaluation, not scientific developmental standards. Density
ranges are configurable hard checks for now. Vocabulary, sentence length,
complexity, pacing, repetition and narrative variety remain soft guidance.
Babies prioritize adult read-aloud sensory experiences without required conflict.
Intentional refrains are allowed; variation must remain appropriate to the age.
No universal six-beat structure is imposed.

Operational page/token sizing lives in `validation/page_policy.py`, separate from
developmental data and graph routing. `RuntimeConfiguration.page_policy` supports
explicit overrides; fake/local composition can inject `Resources.page_policy`
and `Resources.profiles_v2`. Changing a bound or density requires no graph edit.

## Structured education and deterministic checks

`structure.kind: "ordered_targets"` assigns exactly one target to each page in
the supplied order. Each target has a unique `target_id`, exact `label`, and
`kind` (`concept` or `letter`). Alphabet requests require letter targets with
unique labels. There is no server-owned Hebrew alphabet list in orchestration.
Other educational books can supply ordered concepts without alphabet behavior.

Optional `base_form` and `example_word` model a word-final form generally. A
final-form target requires a different base, an example ending with its exact
label and, for alphabet books, an earlier base target. This is a strict literal
contract, not linguistic validation of arbitrary scripts or vocalization.
Optional `sentence_units_per_page` specifies minimum/maximum entries. An
impossible minimum greater than the page's maximum word count is rejected early.

The Planner must emit exactly N numbered intents, each with a nonempty
`progression` contribution and assigned target. The Writer must emit exactly N
pages, matching target order, metadata and density. Outputs are fully validated
locally even when an adapter projects a less restrictive provider schema.
Incomplete output fails or recovers inside the same shared budget; no partial
book is accepted. Stable page IDs must be retained on rewrites.

The Quality Gate checks count, declared count, numbering, unique IDs, target
sequence, exact requested title, sentence-unit count, density, exact target-label
presence and supplied base/example presence. Existing name, metadata, script,
Unicode and narrow safety checks remain. New issue codes include
`TARGET_SEQUENCE_MISMATCH`, `TARGET_LABEL_MISSING`, `TARGET_BASE_FORM_MISSING`,
`TARGET_EXAMPLE_MISSING`, `SENTENCE_UNIT_COUNT` and `TITLE_MISMATCH`.
Malformed structures use `STORY_SCHEMA_INVALID`; coherent but wrong requested
length uses `PAGE_COUNT_MISMATCH`. Some failures are caught before the gate by
stage context validation and receive bounded schema recovery instead.

`FORMULAIC_PAGE_REPETITION` and `NARRATIVE_COVERAGE_REVIEW` are advisory.
Repeated complete pages are flagged for review, not rejected automatically.
Targets alone cannot prove one educational focus, correct final-form teaching,
meaningful progression, varied prose, safety, fluency or active hero agency.
Other letters naturally occur inside ordinary words. Human review remains
necessary; no semantic judge or moderation service was added.

## Bounded execution

`ExecutionContracts` selects versioned schemas, normalizer and prompts at engine
composition. The same four-node LangGraph, adapters and request-local ledger
serve both versions. Planner and Writer model selection stays independent;
there are no provider fallbacks or additional calls for education.

The initial configurable sizing heuristic is:

```text
planner output = 200 + 96 × pages
writer output  = 200 + 256 + pages × (40 + ceil(max_words_per_page × language_ratio))
language_ratio = 2.0 for English; 4.0 for Hebrew
```

Every coefficient belongs to versioned `PagePolicy`, including a thinking/output
allowance. These are provisional admission estimates, not tokenizer guarantees
or guarantees that a model can complete a book. Selected allocations must fit
the existing configured Planner/Writer ceilings, model capacities, aggregate
reservation budget and deadline. They never raise those ceilings automatically.

Before any provider invocation, v2 checks capacity for two worst-case inputs
plus the allocated outputs and corresponding stage tariffs. Each subsequent
attempt keeps existing input/schema reservations and mandatory-writer checks.
Three total attempts and one quality rewrite remain the maximum. Unknown usage
retains reservations; an estimate is not an invoice cap. No automatic deadline
extension, chunking, continuation or extra request is added. Defaults remain
1,200/3,000 stage ceilings, 8,000 input, 30 seconds/attempt and 90 overall; those
defaults do not promise every 1–32-page request fits every profile.

## Roy acceptance case and safe live prerequisites

The exact request is [roy-alphabet-request.v2.he.json](examples/roy-alphabet-request.v2.he.json):
age 36 months, 27 pages, light preschool density, requested Hebrew title, all 22
base letters followed by 5 final forms, ordered target IDs, literal base/example
pairs and 2–3 sentence units per page. The supplied masculine pronouns are
explicit data, not inferred; confirm them when approving a live test.

Offline tests run the full graph/API and both real adapters over mock transports.
Their synthetic filler text proves contract plumbing only; it is not an accepted
educational manuscript or a demonstration of literary quality.

[roy-alphabet-runtime.v2.proposed.json](examples/roy-alphabet-runtime.v2.proposed.json)
is an isolated **proposal**, not an activated production setting or live approval:

| Control | Proposed value |
| --- | --- |
| Gemini stage models | `gemini-3.5-flash-lite` for both stages, inherited declared metadata |
| Output ceilings | Planner 3,000; Writer 6,000 |
| Resolved output allocations | Planner 2,792; Writer 4,128 |
| Input reservation cap | 32,000 per attempt |
| Aggregate tokens | 111,000 |
| Calls / quality rewrites | At most 3 / at most 1 |
| Deadlines | 45 seconds per attempt; 135 overall |
| Internal request cost limit | $0.075, proposed separately from the newborn $0.015 limit |

At the file's declared $0.30/million input and $2.50/million output rates,
two full-cap inputs and allocated outputs reserve $0.03650. The larger permitted
three-attempt path (planner + two writers) reserves 107,048 tokens and $0.05642.
A planner-retry path is smaller. Actual usage can be lower; future output/input
length and successful completion are not guaranteed. These rates/capabilities
were inherited from the earlier proposal and **not reverified online here**.
Recheck official model availability, schema support, prices and overhead before
requesting paid approval. Offline schema projection does not establish live
model compatibility.

The original $0.015 budget cannot admit this conservative two-stage reservation;
it is preserved and explicitly fails admission for Roy. Do not reuse or silently
increase the newborn runtime. Approve the isolated proposed limits explicitly,
including data/pronouns and exactly one end-to-end request, before any paid POST.
Use `/v2/stories/generate` with the exact request above; the old proposal's v1
request/profile override is superseded and must not be used.

Preparation checklist: rerun offline preflight below, verify current provider
metadata, keep the local key private, load it through the existing explicit
credential flow, opt in only after approval, and use the reviewed runtime file.
Do not enable billing, modify Cloud settings or automatically repeat a failed
request. Review every resulting page for Hebrew, sentences, letter teaching,
continuity, Roy's agency, age fit and read-aloud rhythm before product acceptance.

Safe PowerShell checks (no credentials, no network, no paid requests):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_v2_contracts.py tests/test_v2_execution.py tests/test_v2_providers.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_v2_providers.py::test_roy_configuration_and_worst_case_recovery_budget -q
```

Open decisions: v1 retirement date; evaluation/calibration of developmental
densities and sizing coefficients; older-child subdivisions; semantic review
thresholds; future automatic mode, languages and providers; explicit live-test
budget/model approval. No Milestone 7 implementation is included.
