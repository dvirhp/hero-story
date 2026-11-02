# AI design

> Approved page-count update: new work uses [explicit-length v2](PAGE_COUNT_V2.md). The user supplies page_count; age controls developmental guidance and page density. Deprecated v1 keeps its original behavior. Historical milestone sections below describe v1 unless labeled v2. No live calls were made in this follow-up; Milestone 7 remains unapproved.

## Model strategy

Milestone 4 exposes the existing fake-only engine through FastAPI. Its default `LocalFixtureProvider` delegates to scripted `FakeProvider` steps built from the normalized brief; no real semantic generation or moderation service is added. The HTTP layer does not change prompts, budgets, retries or quality policy. See [API behavior](API.md). Milestone 5 adds OpenAI with explicit capacities/pricing and stage model overrides; fake remains the default.

Use one configurable provider/model initially for both planning and writing. Allow optional per-stage model overrides through validated settings, without introducing routing agents. Select the first real model using a small Hebrew/English evaluation, schema adherence, latency, and cost; OpenAI is the first implemented vendor; exact model IDs, rates and spend ceilings remain explicit deployment decisions.

Define an asynchronous provider protocol accepting stage, versioned instructions, validated input, output schema, output-token cap, and remaining deadline. Return validated payload or a normalized error plus usage metadata. Prefer native schema-constrained output. For adapters lacking it, request JSON and validate locally; malformed output uses the same bounded recovery budget. No silent provider fallback. Disable SDK automatic retries.

The fake provider serves scripted typed results, malformed responses, timeouts, and usage records. It must never instantiate a network SDK. Provider-specific SDK types do not cross the adapter boundary.

## Prompts and structured outputs

- Planner: return `StoryPlanV2` (legacy: `StoryPlan`), with exactly the user-requested page count and a progression contribution per page; use the resolved developmental strategy and page intents. Baby stories can be soothing sensory sequences or refrains without conflict. For profiles requesting a plot, use the configured goal/obstacle/resolution requirements rather than a universal six-beat structure.
- Writer: return `StoryV2` (legacy: `Story`); follow the exact requested count, validated plan and selected per-page density, vocabulary, soft sentence targets and repetition guidance, exact display name, and requested language. Baby stories are written for an adult's voice, rhythm, pauses and closeness, not independent reading.
- Input Validation resolves `age_months` (including zero) to a versioned profile outside orchestration logic. Both prompts receive its immutable language-specific snapshot; neither model chooses age bands or infers reading ability. Treat all developmental and word-count targets as initial product hypotheses requiring evaluation.
- Keep shared safety and output requirements in trusted instructions. Pass user text as clearly delimited data; it cannot override instructions, budgets, language, or schemas.
- Maintain English and Hebrew requirement blocks. Generate directly in the target language. Hebrew requires consistent grammatical agreement, natural phrasing, and preservation of the supplied name; English requires pronoun consistency. Avoid gendered references if pronouns are absent; reject combinations the supported rubric cannot handle rather than guessing.
- Assign prompt and rubric versions; record these alongside model identity. Sampling settings are adapter capabilities and must be validated, not assumed portable.
- On one allowed rewrite, include the validated plan, prior draft, and explicit repairable issues. Schema repair uses concise validation feedback; never request hidden reasoning.

## Quality Gate

Run inexpensive local checks first: schema shape, ordered pages matching the requested count (legacy v1: resolved profile count), nonempty title/text, profile-specific hard per-page and total-word limits, name preservation at least once, direction metadata, and forbidden control characters. Do not reject baby stories for lacking a conflict or a six-beat plot. Sentence-length and vocabulary targets are soft review signals, not independent-reading or developmental assessments. Keep Unicode text and logical order; never reverse Hebrew strings. Reject embedded bidi override/isolate controls in user inputs to prevent misleading rendering. Output direction is metadata, not a print-layout implementation.

Language checks use a configurable letter-script ratio excluding punctuation, digits, and the supplied name. Proposed starting threshold: 80% Hebrew letters for `he`, 80% Latin letters for `en`. This detects obvious language mismatch, not fluency. Local content rules detect explicit prohibited content but cannot guarantee safety. Semantic coherence, subtle safety, reading level, and Hebrew agreement need human evaluation; a second LLM judge is outside the initial call budget and requires a later decision.

Milestone 2 supersedes the proposed insufficient-evidence rejection: below the configurable minimum (initially 20 body letters), including zero eligible letters, report `LANGUAGE_EVIDENCE_INCONCLUSIVE` as advisory. Hard checks can still permit overall deterministic acceptance, but no language-verification claim is made. This explicit policy permits short baby refrains and applies to all profiles; stricter release handling remains an open decision. Enough evidence below the configured 80% target-script ratio yields repairable mismatch. Repeated refrains are intentional when suggested by the profile, not generic duplication defects. Human reviewers assess read-aloud flow, vocabulary, natural repetition, reassuring tone, and profile-appropriate coherence in both languages. Word counts and sentence metrics do not establish developmental suitability; Hebrew morphology makes direct English/Hebrew comparisons unreliable.

Classify issues as repairable (length, obvious language mismatch, missing personalization) or terminal (unsafe content). Unsafe input/output and provider safety refusals terminate without repair. Never accept a draft with outstanding hard failures. Quality rules and thresholds are versioned and exercised on both accepted and rejected fixtures.

The pure Milestone 2 implementation and exact limitations are documented in [Validation and Quality](VALIDATION_AND_QUALITY.md). It uses narrow whole-sentence directive matches instead of broad keyword bans, has no moderation service or LLM judge, preserves text and reports soft observations without inferring semantic or developmental correctness. Milestone 3 implements graph routing, scripted provider refusals and bounded rewrites; see [Orchestration](ORCHESTRATION.md).

## Cost, attempts, and time

Proposed configurable defaults, subject to model evaluation:

| Control | Proposal |
| --- | --- |
| Normal path | 1 planner + 1 writer attempt |
| Global maximum | 3 attempted provider invocations total, including transport retry, schema repair, or rewrite |
| Quality rewrites | At most 1, only if a call slot remains |
| Output caps | Planner 1,200 tokens; writer/rewrite 3,000 tokens each |
| Input cap | 8,000 tokens per call including instructions, schema, and repair context |
| Time | 30 seconds per attempt, 90 seconds total including local work; cap each attempt by remaining time |
| Cost | Deployment-configured USD ceiling, approved before real-provider use; no invented universal price |

Before each invocation, reserve a conservative input/output cost bound and a call slot. Validate available capacity for mandatory remaining stages; a planner retry must leave a writer slot. Do not start a call if its upper bound exceeds the remaining budget. Use provider tokenization when available; otherwise a documented conservative bound. Refuse unsupported pricing/capabilities rather than claim a reliable cost ceiling. Cache-token discounts are ignored for reservation.

Output caps are technical starting ceilings, not word targets. V2 selects bounded per-book allocations through PagePolicy; estimates must fit existing ceilings. Allocations must remain sufficient for structured output in both languages. Validate profile lengths against model/context and cost capacity at startup; profile configuration cannot increase the three-attempt maximum or bypass budget checks.

Record provider-reported input/output tokens when present, including cached/reasoning tokens if applicable, and price using a versioned configured rate table. Do not double-count token categories. Record monotonic call duration and total end-to-end latency, including retries and local work. Distinguish reported usage from estimates. Failed attempts with unavailable usage remain unknown, never zero: retain their conservative reservation and expose known cost plus an upper estimate. Pricing estimates are not billing guarantees.

Milestone 3 uses only fake pricing (`fake-zero-v1` by default; optional explicitly synthetic test rates) and a versioned UTF-8-byte input reservation policy, including schema overhead. Aggregate default capacity is 33,000 reservation units. Known usage/cap overruns fail; unknown usage retains the entire conservative reservation. This is not a real tokenizer or billing guarantee. A planner reservation must leave worst-case writer capacity in attempts/tokens/cost. Synthetic latency advances the effective deadline without sleeping; wall-clock timeouts still guard cooperative waits. Milestone 5 adds cached/reasoning subsets, Retry-After, explicit capacity/rate validation and a documented conservative input estimate; verified model metadata and paid-run approval remain required. See [implemented limits](ORCHESTRATION.md).

## Failure handling

| Failure | Behavior |
| --- | --- |
| Invalid or unsafe input | Stop before paid calls |
| Malformed structured output | One recovery attempt if shared budget and required future stages permit |
| Transient network/rate-limit error | Retry only inside shared budget/deadline; respect Retry-After when feasible |
| Authentication, unsupported schema/model, provider refusal | Terminal; configuration issues should be detected at startup when possible |
| Local repairable quality failure | Rewrite once if capacity remains, then rerun all checks |
| Unsafe output, exhausted budget, repeated failure | Typed terminal failure; no partial success |
| Deadline or cancellation | Cancel local await and stop further calls; remote billing may still occur |

No retries in HTTP handlers or hidden adapter layers. Bound retry backoff by the deadline. Do not log child names, story text, guidance, credentials, or raw provider errors by default. Use request IDs, stage/outcome codes, model/prompt versions, token/cost metadata, and latency. No content persistence in MVP.

## Evaluation and open decisions

Prepare a small reviewed fixture set across both languages, every proposed age band (including `age_months: 0`), gendered/ungendered narration, difficult names, injection attempts, unsafe requests, and profile-specific length boundaries. See the offline matrix in the Roadmap. Offline tests establish contracts and routing, not real-model developmental quality. Paid evaluation is explicitly opt-in, separately budgeted, and reviewed by fluent speakers and adult readers; never part of default pytest. Provider choice, pricing ceiling, age-band boundaries/strategies/targets, older-child subdivisions, language thresholds for short text, and human release criteria remain open. No developmental efficacy claims are made.

## Gemini-specific execution (Milestone 6)

The official async adapter reuses existing prompts, schemas and quality policies. Native JSON schema uses a pure provider projection with full strict local validation. HTTP retries, automatic continuation and automatic tools are disabled. Gemini candidate tokens exclude thinking; normalized output adds reported thoughts exactly once and reconciles totals. Input caches remain a subset. Missing/inconsistent usage and missing prices remain independently unknown. Model IDs, capacities and tariffs are explicit per-stage configuration, never age/language branches in the graph. See [Gemini design, caveats and proposed live test](GEMINI.md). No paid evaluation or new language is included.

## V2 education, repetition and cost admission

Both v2 prompts receive typed ordered targets as untrusted data and require an age-appropriate continuous arc or sensory sequence. They allow intentional refrains while requesting gentle variation of actions, discoveries and page openings. Structured target IDs, literal labels/examples, count and sentence-unit entries are deterministic contracts; correctness of explanations, grammar, agency and progression require human review. There is no additional LLM judge or per-letter provider call.

V2 sizing scales with N and selected density and rejects insufficient configured capacity before a provider call. It never raises model ceilings, attempts, cost or timeouts automatically. Three shared attempts, one rewrite and held unknown-usage reservations remain unchanged. The [v2 design](PAGE_COUNT_V2.md) documents versioned coefficients, exact hard checks, limitations, Roy's proposed isolated runtime and its separately required live approval. Original newborn limits remain unchanged.
