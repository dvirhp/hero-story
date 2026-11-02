# Implementation roadmap

Milestones 1–4 are approved and implemented. Milestone 5 and later await separate approval. Each should be a small reviewable change; no frontend or infrastructure work.

| Milestone | Deliverables | Required validation |
| --- | --- | --- |
| 1. Contracts and offline foundation | `pyproject.toml`, Python 3.12+ package skeleton, Pydantic contracts with strict nonnegative `age_months`, separate versioned developmental configuration and pure resolver, settings, provider protocol and scripted fake; runnable setup instructions | Offline bilingual contracts and profile resolution across newborn/infant/toddler/preschool/older-child bands; strict age and configuration validation, variable page/plan contracts, fake success/error scripts; import/package smoke check |
| 2. Validation and quality rules | Normalization with immutable profile snapshot, language rubrics, profile-aware deterministic quality reports, safe error types | Fixtures for both scripts, niqqud, names/pronouns, bidi controls, per-profile length boundaries, intentional repetition, plot-free baby stories, unsafe/repairable classification; document semantic limits |
| 3. Bounded LangGraph engine | Four nodes, explicit conditional routes, prompt versions, attempt ledger, deadlines and conservative budget reservations | Fake-provider paths: success, zero-call rejection, planner/writer schema repair, transient failure, rewrite success/failure, safety stop, cancellation, unknown usage; never over three attempts; use fake clock for deadline tests |
| 4. FastAPI boundary | Generate endpoint, health endpoint, dependency injection, response/error envelopes and OpenAPI examples | HTTPX ASGITransport with explicit lifespan and fake providers: accepted stories in both languages, error/status mapping, request IDs, validation envelope, no failed drafts or sensitive diagnostics |
| 5. First real adapter | One selected provider, capability validation, structured outputs, pricing config, normalized usage, explicit no-retry SDK setup | Mock transport adapter-contract tests for usage, malformed JSON, refusal, timeout, rate limit, unknown usage and retry counts; default suite remains offline |
| 6. Bilingual evaluation and tuning | Reviewed evaluation set spanning all profiles, adult read-aloud trials, opt-in runner and cost report, tuned prompts/rubrics/profile targets, documented limitations and release checklist | Approved small paid trial plus fluent human review; assess baby read-aloud flow and profile-appropriate coherence; report acceptance, quality defects, token/cost and latency distributions; verify budgets and no unaccepted stories escape; no scientific validation claim |

## Milestone 1 scope and stop boundary

Milestone 1 establishes typed contracts, separate declarative developmental configuration and pure resolver, and an entirely offline provider seam before graph or HTTP implementation. It includes `age_months: 0`, no assumed upper age limit, and profile-dependent page counts and strategies. The five provisional profiles, hard page/word constraints and soft guidance are approved. Pronouns have explicit language-tagged forms; curated presets remain open. No provider SDK or credentials are installed or required.

## Milestone 2 scope and stop boundary

Pure request normalization, deterministic hard checks, non-blocking profile-aware observations and sanitized reports were implemented without changing Milestone 1 tests. See [implemented policies](VALIDATION_AND_QUALITY.md), including advisory inconclusive script evidence rather than the superseded rejection proposal. That milestone introduced no graph, prompts, HTTP endpoints or dependencies. Model-specific capacity checks remain in the real adapter milestone.

Verification: 270 passed, 0 failed on Windows/Python 3.12.16 and 3.13.3, including the original 115 tests. The two new test modules contain 155 normalization/quality cases; all run offline.

## Milestone 3 scope and stop boundary

Implemented: one compiled four-node LangGraph, typed immutable state and request-local journal, language-aware versioned prompts, shared three-attempt limit, one quality rewrite, conditional schema/transport recovery, time/token/cost reservations, unknown usage accounting and cancellation. Existing 270 tests are preserved. An optional sanitized quality report on provider failures closes the malformed-output safety gap without returning raw responses. See [execution and Git workflow](ORCHESTRATION.md). No real provider, HTTP endpoint, remote Git repository, push or deployment is included. Stop until Milestone 4 is approved.

Verification: 330 passed, 0 failed on Windows/Python 3.12.16 and 3.13.3; wheel and source distribution builds passed. The original 270 tests are unchanged; 60 new cases cover execution/foundation behavior.

## Milestone 4 scope and stop boundary

Implemented: a FastAPI application factory, lifespan configuration, async dependency injection, `/health`, `/v1/stories/generate`, strict domain JSON validation, sanitized failure/status mappings, request IDs, and request-scoped disconnect/cancellation cleanup. The default local fixture adapter shares the existing demo fixtures and delegates to `FakeProvider`; it is not a real LLM integration. Original 330 tests remain unchanged. See [API reference and commands](API.md). No remote, push, merge or deployment is included. Stop until Milestone 5 is approved.

Verification: 393 passed, 0 failed on Windows/Python 3.12.16 and 3.13.3, with 63 new cases and the original 330 unchanged; wheel/source builds and an isolated installed-wheel API smoke check passed.

## Proposed offline test matrix

Run story/profile fixtures for both `he` and `en`; pure normalization/quality fixtures need no provider. A scripted fake is reserved for provider/graph paths in their milestones. No credentials or network are needed. Use the Product Spec's proposed configuration as a replaceable test fixture, not scientific ground truth.

| Cases | Expected checks |
| --- | --- |
| Newborn: 0, 2 months | Resolve newborn profile; accept four short pages of soothing sensory refrains without conflict; require adult-read-aloud metadata/guidance in normalized profile and prompts |
| Infant: 3, 11 months | Resolve infant profile; accept repeated noticing/sounds; enforce its own page/word limits rather than 30–60 words/page |
| Toddler: 12, 35 months | Resolve toddler profile; accept five-page familiar routine and repeated action; no mandatory six-beat plot |
| Preschool: 36, 71 months | Resolve preschool profile; six-page simple goal/obstacle/resolution fixture with its configured lengths |
| Older child: 72, 120, 180 months | Resolve open-ended older-child profile without an invented upper cutoff; use richer connected scenes and profile-specific lengths; do not infer independent-reading ability |
| Every adjacent boundary | 2/3, 11/12, 35/36, 71/72 months each resolve exactly one profile; zero is included |
| Invalid age | Reject negative, fractional, boolean, string, missing or null `age_months`; no conversion from years; zero paid calls |
| Invalid configuration | Reject gaps, overlaps, missing zero coverage, finite final maximum, unsupported strategy, missing language, inconsistent page/total-word ranges, and profile lengths exceeding technical capacity |
| Profile-specific output boundaries | Pass exact hard minima/maxima; report below/above-range counts and wrong page count; soft sentence-target violations do not automatically fail; revision retains profile ID/version |
| Configuration extensibility | Split older-child band or change toddler page count in a fixture; resolver, plan validation, prompts and quality rules change together without graph edits; active request retains its snapshot |
| Short bilingual baby text | Hebrew with niqqud, names excluded from script ratio, intentional repeated sounds, and zero eligible letters; deterministic inconclusive-language handling, no division by zero |
| All profiles: graph and API | Accepted result, malformed output, refusal, quality rejection, exhausted retry budget and sanitized errors; profile-aware checks never increase the three-attempt bound |

Offline assertions establish configured behavior. Fluent adult reviewers separately assess natural Hebrew/English, read-aloud rhythm, vocabulary, repetition and age fit; tests do not certify those qualities.

## Gates and later work

- Before milestone 5: choose provider/model, current pricing, supported token counting, and a real-request cost ceiling.
- Before final profile approval: evaluate month boundaries, narrative strategies, language-specific word/sentence targets, hard versus soft checks, and older-child subdivisions. An upper audience limit requires an explicit product decision.
- Before any wider release: agree bilingual quality thresholds, adult-facing product wording, privacy/retention approach, authentication, abuse and aggregate-spend controls.
- Later product phases: illustrations, user editing, templates, persistence, and print layout. Plan them separately when required; preserve versioned contracts rather than implement speculative hooks.
