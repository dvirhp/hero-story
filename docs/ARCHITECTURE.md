# Architecture

> Approved page-count update: new work uses [explicit-length v2](PAGE_COUNT_V2.md). The user supplies page_count; age controls developmental guidance and page density. Deprecated v1 keeps its original behavior. Historical milestone sections below describe v1 unless labeled v2. No live calls were made in this follow-up; Milestone 7 remains unapproved.

Status: Milestones 1 through 6 implemented. Fake is the default; OpenAI/Gemini are available only by explicit opt-in. Developmental profiles remain provisional hypotheses. Milestone 7 requires separate approval.

## Boundaries

Package layout (Milestones 1 through 6 implement these boundaries; OpenAI and Gemini are the real adapters):

| Location | Responsibility |
| --- | --- |
| `src/storyforge/api/` | HTTP schemas, dependency wiring, status mapping; no prompts or provider logic |
| `src/storyforge/domain/` | Pydantic contracts, constraints, policy types; independent of FastAPI and provider SDKs |
| `src/storyforge/development/` | Versioned declarative age-band data, typed profile validation and pure month/language resolver; independent of orchestration and providers |
| `src/storyforge/orchestration/` | Graph, four nodes, routing, bounded execution state |
| `src/storyforge/prompts/` | Versioned planner/writer instructions and Hebrew/English requirements |
| `src/storyforge/llm/` | Provider protocol, fake adapter, selected real adapter, usage normalization |
| `src/storyforge/quality/` | Pure deterministic checks and versioned language rubrics |
| `src/storyforge/validation/` | Pure request normalization, safe validation errors and profile resolution |
| `src/storyforge/config.py` | Validated settings and model capabilities; no secrets in source |
| `tests/` | Unit, graph, API, adapter-contract, and opt-in evaluation tests |

API and graph depend on domain contracts. Nodes use the provider protocol and prompt builders. Adapters depend on their SDK, never the reverse. Construct dependencies at the application boundary; avoid global clients in domain modules.

## Developmental configuration

Resolve strict integer `age_months >= 0` during Input Validation. Do not accept years as an alternate internal representation, infer age from a birth date, or impose an unapproved maximum. Configure ordered `[min_months, max_months)` bands starting at zero, with a null final maximum for open-ended coverage. Reject gaps, overlaps, missing language profiles, invalid lengths, and unsupported narrative strategy IDs at startup.

Each `DevelopmentalProfile` contains stable band ID/version, month bounds, language-specific read-aloud mode, narrative strategy, vocabulary guidance, soft sentence-length targets, repetition guidance, and density recommendations with explicit hard/soft classifications. V2 developmental data contains no page counts or total-book lengths. Normalization derives total word ranges from user page count times selected density. Legacy v1 retains its original page/total ranges. The initial values are product hypotheses documented in the Product Spec, not scientific standards. Treat them as versioned declarative data rather than executable prompt fragments or age-based branches inside graph nodes.

Milestone 1 packages this data in `development/profiles.v1.json` and loads it explicitly using package resources. Nested frozen models and tuples keep snapshots immutable. Python model construction is strict (tuple collections); JSON boundaries accept JSON arrays. `StoryPlan.validate_for(brief)` and `Story.validate_for(brief)` explicitly enforce context-dependent structural contracts; constructing a standalone output cannot establish profile compliance or quality approval.

Pronouns use a language-discriminated contract: English specifies subject/object, possessive determiner/pronoun, reflexive and singular/plural verb agreement; Hebrew specifies subject/object, possessive and masculine/feminine singular agreement. Forms are supplied explicitly, not generated from names. These are technical representations of supplied forms, not curated product presets or guarantees of grammatical correctness. Additional agreement support needs a reviewed contract change. Omitted pronouns remain absent.

Settings are explicitly constructed or validated from supplied mappings/JSON; Milestone 1 reads no environment variables or secrets and supports only the fake provider. Model tokenization, pricing and model-specific capacity validation remain part of the real adapter milestone; no fake token/word conversion is presented as a capacity guarantee.

Milestone 2 adds `normalize_request` and `assess_story` as independently testable pure functions, not graph nodes. They share immutable injected `QualityRules` configuration and reuse `GenerationError`/`QualityReport`. Normalization resolves profile and rubric context without rewriting user text. Quality assessment accepts a typed story, JSON or mapping and sanitizes schema failures into reports. See [implemented interfaces and issue codes](VALIDATION_AND_QUALITY.md). Any terminal issue takes precedence over repairable issues. Advisory observations never block acceptance; inconclusive language evidence is explicit and does not claim language verification.

Resolve and snapshot one immutable profile per request so a configuration update cannot change it midway. Planner, writer, and quality checks consume that same snapshot. Band changes require no graph-routing changes. Baby profiles permit sensory sequences/refrains without a problem-resolution arc. No node imposes a universal six-beat plot or six-page count.

## Graph

```mermaid
flowchart TD
    S([START]) --> V[Input Validation]
    V -->|valid| P[Story Planner]
    V -->|invalid or policy rejection| E([END: failure])
    P -->|validated plan| W[Story Writer]
    P -->|recoverable and budget remains| P
    P -->|terminal failure| E
    W -->|validated draft| Q[Quality Gate]
    W -->|recoverable and budget remains| W
    W -->|terminal failure| E
    Q -->|pass| OK([END: accepted])
    Q -->|repairable and budget remains| W
    Q -->|unsafe or exhausted| E
```

Each node has one routing function with explicit destination literals. Retry and rewrite edges share the same budget; no independent nested retry loops. Quality Gate is deterministic in MVP and makes no LLM calls. A graph recursion limit is a secondary safeguard, not the business call counter.

The implemented graph uses immutable Pydantic `RunState` under a typed `GraphState` and request-local `Session` journaling of pre-await reservations. Only planner/writer call the asynchronous provider. Explicit LangGraph retry policies permit one node attempt; retries occur solely on conditional graph edges. No checkpointer is configured. The public wrapper handles cancellation, deadlines and safe result conversion without exposing internal drafts. Full state, budget, prompt and failure details are in [ORCHESTRATION.md](ORCHESTRATION.md).

## V2 contract composition

`ExecutionContracts` selects v1 or v2 request/output schemas, normalizer and prompts at composition time. Graph nodes, conditional routes, provider protocol, adapters and accounting remain shared. V2 normalizes `StoryRequestV2` into immutable developmental, `BookConstraints` and `ExecutionAllocation` snapshots. Page admission/sizing uses injected `PagePolicy`, outside age profiles and graph routing. V1 never falls back into v2 normalization or vice versa.

The v2 Planner emits N intents with explicit progression and ordered target assignments. The Writer emits N pages with stable IDs and sentence_units; joined text is derived. Both use the same developmental snapshot. The gate checks requested count and structure deterministically; semantic progression remains model work and human review. See [full v2 state contracts and migration](PAGE_COUNT_V2.md).

## Legacy v1 typed contracts (retained for compatibility)

Use Pydantic v2 models with forbidden extra fields and explicit bounds at every untrusted boundary. Use a typed state container for partial graph updates; runtime validity comes from domain-model validation and transition checks, not type hints alone.

| Contract | Required content |
| --- | --- |
| `StoryRequest` | Language, display name, strict integer `age_months >= 0`, theme, optional interests, narrative pronouns, guidance; no assumed upper age limit |
| `DevelopmentalProfile` | Band ID/version and bounds; resolved language-specific strategy, read-aloud mode, vocabulary, repetition, sentence targets, page/word constraints |
| `NormalizedBrief` | Validated request, resolved profile snapshot, language rubric version; constraints derived from configuration |
| `StoryPlan` | Language, title concept, protagonist, strategy ID, ordered page intents matching profile count; strategy-specific narrative elements, with no mandatory conflict for babies |
| `Story` | Schema version, title, language, direction (`rtl`/`ltr`), profile ID/version, variable-length ordered pages with stable request-local IDs, page numbers and text |
| `QualityReport` | Pass/fail; issues with code, severity, optional page number and repair guidance; check/rubric versions |
| `AttemptRecord` | Stage, attempt number, provider/model, prompt version, duration, token counts, usage source, estimated cost, outcome |
| `GenerationError` | Stable code, safe message, stage, retryable flag; no raw prompt or provider response |
| `GenerationResult` | Request ID, discriminated success/failure, accepted story only on success, quality/usage summary and total latency |

Graph state contains request ID, raw typed request, optional normalized brief/plan/draft/report/error, status, attempt records, attempts used, rewrite count, deadline, reserved/estimated cost, and captured configuration versions. Drafts remain internal. SDK objects, secrets, clients, and mutable pricing tables are injected dependencies, not state fields. Request-local state requires no checkpoint store.

Invariants: writer requires a validated plan; quality requires a validated draft; success requires a passing report; every attempted provider invocation consumes a slot before execution; terminal state has exactly one success or failure result. Preserve earlier attempt records through revisions.

Plan and story validation checks page counts and narrative requirements against the resolved profile, not a global six-item schema. Profile ID/version is server-assigned metadata, not an LLM-selected band. Technical output/token limits remain separate from audience age policy; a larger future profile must pass startup capacity validation rather than silently truncate stories or introduce an age cutoff.

## Implemented API

- `POST /v1/stories/generate`: synchronous typed request; HTTP 200 with accepted result.
- HTTP 422: input validation; 400: content-policy rejection; 502: unusable provider output; 503: transient provider unavailability; 504: deadline exceeded. Use 422 with `QUALITY_REJECTED` for a valid request whose generated story fails quality, distinguished by error code.
- HTTP 503 with `BUDGET_EXCEEDED` when generation cannot continue under server limits; configuration errors fail startup.
- Normalize framework validation errors into the documented error envelope. Include request ID and available usage on runtime failures; no failed story text.
- `GET /health`: process readiness only, no paid provider call.

Milestone 4 preserves the planned versioned route and `422 QUALITY_REJECTED` mapping; that code denotes generated quality failure, not necessarily invalid client input. Input-policy rejections map to 400, while provider-produced unsafe content maps to 502 by stage. Internal unexpected/configuration/result failures map to 500; cancellation maps to best-effort 499. Startup configuration errors still fail startup. See [the full mapping](API.md).

The application factory and async dependencies build a request-local engine with the existing default settings and local fixture provider. Resources load in lifespan and contain immutable configuration only. A boundary-only JSON validator preserves domain tuple/strict scalar semantics without parallel story DTOs. Sanitized route/exception handling produces existing success/failure contracts and server-generated request IDs. After body validation, a request-scoped disconnect watcher cancels and awaits engine execution; it is not a background job. No API-layer retries or quality checks are added.

No automatic client retry or idempotency guarantee: repeating a POST is a new generation and may incur cost. Cancellation stops further scheduling; an in-flight remote request may still be billed.

## Extension seams

Stable page IDs and versioned story contracts provide future inputs for illustration and editing. Printing consumes a later layout contract. Add optional stages only with a product requirement and tests; do not prebuild those systems.

## References

The graph design uses explicit [LangGraph conditional edges](https://reference.langchain.com/python/langgraph/graph/state/StateGraph/add_conditional_edges). Validate boundary data using [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/). Verify exact dependency APIs when implementation versions are selected.

## Gemini composition (Milestone 6)

The configured factory selects Fake/OpenAI/Gemini through explicit server configuration, never story input. SDK-specific classes stay inside adapters/composition. Both real providers share existing capability validation and per-stage pricing; a pure composition-time reservation policy selects the appropriate projected schema outside graph nodes. Planner/Writer, conditional routing, Quality Gate and API routes do not gain vendor responsibilities. Gemini credentials, retries/continuation, usage normalization and pool ownership are documented in [GEMINI.md](GEMINI.md).
