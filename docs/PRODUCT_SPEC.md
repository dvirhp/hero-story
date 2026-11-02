# StoryForge AI product specification

> Approved page-count update: new work uses [explicit-length v2](PAGE_COUNT_V2.md). The user supplies page_count; age controls developmental guidance and page density. Deprecated v1 keeps its original behavior. Historical milestone sections below describe v1 unless labeled v2. No live calls were made in this follow-up; Milestone 7 remains unapproved.

Status: Milestones 1 through 6 implemented. Fake is the default; OpenAI/Gemini are available only by explicit opt-in. Developmental profiles remain provisional hypotheses. Milestone 7 requires separate approval.

## Goal

Generate a personalized, age-appropriate children's story from a small, validated brief across worldwide languages over time. Hebrew and English are the currently implemented languages. Return a structured story that can later support editing, illustration, and book production.

## User flow

1. An adult supplies the child's display name, `age_months`, language, theme, explicit page_count, and optional interests, narrative pronouns, and creative guidance. Newborns use `age_months: 0`.
2. The engine validates and normalizes the brief and resolves a versioned developmental profile before any paid call.
3. A planner creates a structured outline; a writer turns it into numbered story pages.
4. A quality gate checks the draft. At most one revision is available within the shared call budget.
5. The API returns an accepted story and generation metadata, or a typed failure. Failed drafts are never returned as successful stories.

## MVP scope

- A synchronous JSON API for AI story generation; no frontend.
- Explicit Input Validation, Story Planner, Story Writer, and Quality Gate graph nodes.
- Provider-agnostic model evaluation and stage-specific model selection, with a deterministic fake provider for offline development and tests.
- Structured requests, outlines, stories, quality reports, errors, and usage records.
- Hebrew and English generation, including explicit narrative pronouns, language checks, and text direction metadata.
- Bounded calls, token limits, timeouts, and estimated cost accounting.

## Proposed product defaults (assumptions)

| Item | Initial proposal |
| --- | --- |
| Audience | Adult requesting a story for a child from birth; no product upper age limit has been decided |
| Age | Required strict nonnegative integer `age_months`; zero includes newborns; no years field or birth date required |
| Language | Required enum: `en` or `he`; no implicit translation |
| Length and structure | V2 requires user page_count within configurable service bounds (initially 1-32); optional ordered learning targets; age selects density and narrative guidance, never book length |
| Personalization | Required display name (1–40 characters); up to 5 interests (1–40 characters each) |
| Creative input | Required theme (1–120 characters); optional guidance up to 500 characters |
| Narrative pronouns | Optional explicit language-tagged forms and grammatical agreement; do not infer from a name; avoid gendered references when absent |
| Tone | Warm, imaginative, reassuring ending; no graphic violence, sexual content, hate, or dangerous instructions |
| Hebrew | Natural modern Hebrew, no niqqud required, RTL metadata, consistent grammatical agreement |
| English | Natural English, LTR metadata, consistent pronouns |

These are starting constraints, not validated educational claims. Developmental profiles guide storytelling rather than diagnose ability or prescribe milestones. Word counts are an engineering length proxy, not equivalent reading difficulty across languages.

## Proposed developmental profiles

All ranges below are initial product hypotheses requiring adult read-aloud trials and bilingual evaluation, not scientifically validated standards. Month intervals are lower-inclusive and upper-exclusive. Profile selection uses age only as a starting signal, not evidence of an individual child's ability. Configuration is maintained separately from graph logic.

| Profile | Months | Experience and narrative strategy | Vocabulary and sentence target | Repetition | Light / standard words per page |
| --- | --- | --- | --- | --- | --- |
| Newborn | 0–3 | Adult read-aloud; soothing sensory moments and closeness; no conflict or plot requirement | Familiar people, sounds, touch; 2–5 words per utterance | A short refrain on each page | 5-10 / 5-15 |
| Infant | 3–12 | Adult read-aloud; gentle noticing and predictable sequences | Concrete familiar objects/actions; 2–6 words/sentence | Recurring sound or phrase | 5-12 / 10-20 |
| Toddler | 12–36 | Adult read-aloud; familiar routine, simple action and reassuring closure | Concrete nouns and verbs; 3–8 words/sentence | Refrain or repeated action | 8-18 / 15-30 |
| Preschool | 36–72 | Shared read-aloud; simple goal, gentle obstacle, resolution | Familiar vocabulary with contextual new words; 5–12 words/sentence | Optional recurring phrase | 12-24 / 25-45 |
| Older child (provisional fallback) | 72 onward | Adult/shared reading by default; connected scenes, character goal, choices and resolution; independent reading is not inferred from age | Richer contextual vocabulary; 8–18 words/sentence | Optional thematic recurrence | 20-40 / 40-70 |

The open-ended final profile ensures coverage without an invented upper age cutoff; it does not assert one strategy suits every older child. Splitting it into additional bands is an open product decision. Sentence length, vocabulary, repetition and developmental guidance are soft targets. User page count and selected density ranges are approved as configurable hard output checks; they remain product hypotheses and may be revised. Counts exclude titles and use whitespace-delimited words initially in both languages. Configurations may provide separate Hebrew/English targets after evaluation.

## Non-goals

Templates, freeform editing, illustrations, accounts, persistence, payments, printing, PDF layout, streaming, background jobs, RAG, tools acting on external systems, and dynamic supervisor agents. Do not add databases, queues, microservices, or hosting infrastructure for this MVP.

## Acceptance criteria

- Invalid shape or unsupported values produce HTTP 422 and zero provider calls. Locally detected unsafe briefs produce a typed policy rejection before generation.
- `age_months: 0` is valid; negative, fractional, boolean, missing, or coerced string ages are rejected. No unapproved upper age cutoff is introduced.
- Successful output has a title and ordered pages matching the requested page count and selected density constraints, preserves the child's display name, and includes language, direction, profile ID, and profile version metadata.
- Both language paths cover newborns, infants, toddlers, preschool children, and older children, including band boundaries, malformed outputs, pronoun handling, and quality rejection.
- Only quality-approved stories receive HTTP 200. Schema, provider, budget, or quality failures have stable machine-readable codes and a request ID.
- Normal generation uses two provider attempts; all recovery combined permits at most three attempts. Every attempt is recorded, including failed attempts with unknown usage.
- Tests run without credentials, network access, or paid calls.
- A reviewed bilingual evaluation set covers profile fit, adult read-aloud experience, narrative coherence appropriate to the profile (including plot-free baby stories), personalization, grammar, and safety. Automated success alone does not establish literary quality or safety.

## Open decisions

Milestone 2 implements pure normalization and deterministic quality assessment; see [implemented rules and limitations](VALIDATION_AND_QUALITY.md). Insufficient script evidence is an explicit non-blocking observation, including zero eligible letters. Overall deterministic acceptance is permitted if hard checks pass, without claiming language verification or safety. Milestone 3 executes the bounded graph with scripted fake outputs only. Milestone 4 adds the [local HTTP API](API.md); Milestone 5 adds an offline-tested OpenAI adapter with explicit real-run configuration; the user subsequently reported a successful newborn smoke test, which does not establish general story quality.

- Evaluate and refine the approved provisional band boundaries, density and sentence targets, repetition strategies, and language-specific overrides through Hebrew/English review and read-aloud evaluation.
- Decide whether/where to split the open-ended older-child profile and whether to introduce an explicit upper audience age; no upper limit is assumed meanwhile.
- Decide future adult-selected reading preferences/ability overrides; MVP uses the age profile and does not assume independent reading. Curated pronoun presets, additional Hebrew agreement forms and linguistic handling of absent pronouns remain to be evaluated; Milestone 1 accepts explicit forms without inferring them or claiming linguistic validation.
- Compare candidate providers and select explicit stage models; approve token prices and per-request cost ceiling after a small bilingual evaluation.
- Decide the release threshold for human evaluation and the intended adult-facing safety wording.
- Public deployment, authentication, abuse controls, retention, and applicable privacy obligations need a separate release decision. MVP assumes local or controlled evaluation access.

## Milestone 6 implementation boundary

Gemini joins OpenAI and Fake through the same engine/API contracts; separate Planner/Writer models and costs are configurable. Only Hebrew/English are enabled today. The user reported success of the separately approved synthetic newborn smoke test. It does not establish literary quality, developmental suitability, safety or production readiness. No additional live call or additional-language rollout is authorized by this follow-up.

## Explicit-length v2 acceptance

- Page count is a strict user input, independent of all five developmental profiles.
- Planner, Writer and deterministic gate preserve exactly N numbered pages; no silent truncation or padding.
- General, bedtime, adventure, educational and alphabet prompts share the same four-node graph.
- Structured ordered targets support exactly one assigned target per page, including generic final-form metadata.
- Roy's Hebrew 27-page alphabet request is an offline structural acceptance case, not a special orchestration path or a validated manuscript.
- API migration keeps deprecated v1 temporarily; new v2 clients explicitly choose count and consume sentence_units.
- Operational admission may reject a valid book whose requested size exceeds configured tokens, cost or deadline capacity.
- Human review still establishes age fit, fluency, teaching accuracy, variety and hero agency. See [contracts, limits and live prerequisites](PAGE_COUNT_V2.md).
