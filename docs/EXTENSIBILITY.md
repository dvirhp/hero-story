# Provider and worldwide-language architecture review

> Approved page-count update: new work uses [explicit-length v2](PAGE_COUNT_V2.md). The user supplies page_count; age controls developmental guidance and page density. Deprecated v1 keeps its original behavior. Historical milestone sections below describe v1 unless labeled v2. No live calls were made in this follow-up; Milestone 7 remains unapproved.

Decision: no major graph or domain redesign is needed. Keep the four nodes, typed outputs and shared request budget. Milestone 5 implements OpenAI; Milestone 6 adds Gemini and preserves all preceding work. The long-term product requirement now covers worldwide languages and comparison of OpenAI, Gemini, Claude and potentially others. That requirement is not a claim of current support.

## Provider extension

The async `LLMProvider.generate(request, output_schema)` protocol has no SDK types. Prompts, domain objects and quality assessment remain provider-independent. The OpenAI adapter owns Responses schema projection, SDK calls, response parsing and error normalization. No supervisor, tools or dynamic model routing is needed.

Implemented now: explicit Planner/Writer model overrides, per-stage capability/pricing declarations and ledger entries. Writer reservations use the writer tariff even before the planner is called. One configured provider client can serve both models. Configuration rejects mismatched metadata and unsupported runtime providers. Pricing identifiers are provider-neutral; accepting a metadata label does not implement its adapter.

Proposed later: provider-specific composition factories behind the existing protocol; per-stage provider bindings with provider/model keys (model IDs alone are not globally unique). Select schema translation, token reservation policy and optional output capabilities by adapter. Preserve nullable unknown usage/cost, one shared attempt ledger, sanitized errors and zero hidden SDK retries. Milestone 6 moves reservation selection to a composition-time policy outside graph nodes and validates capacities for either real provider. Avoid speculative general-purpose registries now.

Evaluate models offline first using shared fixtures, then separately approved paid trials. Compare quality by language and developmental profile, personalization, read-aloud rhythm, grammar, safety defects, acceptance rate, latency and total generation cost including failures/retries. A cheaper call can produce a more expensive accepted story. Do not automatically fail over providers without approved privacy, budget and quality policy.

## Language extension

Current constraints are deliberately `he`/`en`, including domain literals, discriminated pronoun shapes, profile language maps, prompt requirements, script checks, sentence observations and whitespace word counts. Adding enum values alone would produce incomplete validation and misleading quality results. Unsupported languages continue to fail before provider calls.

Proposed later changes, separate from orchestration:

- Versioned registry of approved canonical language/locale identifiers, aliases and explicit fallback policy; decide BCP 47 locale handling before changing the public contract. Store language/direction/profile/rubric versions in the normalized snapshot.
- Declarative language-specific developmental guidance for all five bands, with reviewed vocabulary, repetition and read-aloud strategies. Age remains months from zero, with no upper cutoff or universal plot structure.
- Explicit language-specific pronoun and agreement contracts. Support languages without gendered pronouns and differing agreement systems. Never infer forms from names, translate names or silently substitute a language.
- Pluggable pure text segmentation/count policies for languages without whitespace, mixed scripts, combining marks, abbreviations and punctuation. Revise hard word targets with product approval; current whitespace rules are not universal.
- Direction, allowed script mixtures and inconclusive-evidence rules per language. Script evidence cannot verify language or fluency; many languages share a script. Review safety vocabulary/rubrics per language without claiming exhaustive moderation.
- Language-aware prompt builders consume the registry/profile snapshot; graph routing remains unchanged. Each pack needs native-speaker and adult read-aloud review before release, not just automated acceptance.

## Open decisions

Initial additional languages/locales and rollout order; canonicalization/fallback behavior; script/segmentation libraries and counting units; agreement contract evolution and API compatibility; reviewed hard page/word targets; older-child subdivisions; provider/model shortlist per language; verified capabilities and reservation overhead; current tariffs/spend ceilings; evaluation data, reviewer thresholds, privacy/retention and live-run approval. None is silently settled by this milestone. Developmental rules and length targets remain provisional product hypotheses, not scientific standards.

The proposed delivery slices and tests are in [ROADMAP.md](ROADMAP.md). Gemini is now implemented; Claude, multilingual registry and live evaluation remain unimplemented. No Milestone 7 work is authorized.

## Gemini-specific multilingual readiness

Gemini preserves Unicode and consumes existing language/profile snapshots. Its own language coverage is not an application-support guarantee. Stage token caps include thinking; UTF-8 reservations and observed token rates vary by script. Revisit per-language caps, segmentation, pronouns and native-review evidence when adding a language. No new language restriction or translation fallback is introduced. See [Gemini limitations](GEMINI.md).
