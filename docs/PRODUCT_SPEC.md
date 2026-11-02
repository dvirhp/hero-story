# StoryForge AI product specification

Status: Milestones 1–3 approved; later milestones require separate approval. The five developmental profiles and hard page/word constraints are approved as provisional configuration, not validated developmental standards.

## Goal

Generate a personalized, age-appropriate children's story from a small, validated brief in Hebrew or English. Return a structured story that can later support editing, illustration, and book production.

## User flow

1. An adult supplies the child's display name, `age_months`, language, theme, and optional interests, narrative pronouns, and creative guidance. Newborns use `age_months: 0`.
2. The engine validates and normalizes the brief and resolves a versioned developmental profile before any paid call.
3. A planner creates a structured outline; a writer turns it into numbered story pages.
4. A quality gate checks the draft. At most one revision is available within the shared call budget.
5. The API returns an accepted story and generation metadata, or a typed failure. Failed drafts are never returned as successful stories.

## MVP scope

- A synchronous JSON API for AI story generation; no frontend.
- Explicit Input Validation, Story Planner, Story Writer, and Quality Gate graph nodes.
- Configurable provider and model, with a deterministic fake provider for offline development and tests.
- Structured requests, outlines, stories, quality reports, errors, and usage records.
- Hebrew and English generation, including explicit narrative pronouns, language checks, and text direction metadata.
- Bounded calls, token limits, timeouts, and estimated cost accounting.

## Proposed product defaults (assumptions)

| Item | Initial proposal |
| --- | --- |
| Audience | Adult requesting a story for a child from birth; no product upper age limit has been decided |
| Age | Required strict nonnegative integer `age_months`; zero includes newborns; no years field or birth date required |
| Language | Required enum: `en` or `he`; no implicit translation |
| Length and structure | Selected by configurable developmental profile; no universal page count, word range, or six-beat plot |
| Personalization | Required display name (1–40 characters); up to 5 interests (1–40 characters each) |
| Creative input | Required theme (1–120 characters); optional guidance up to 500 characters |
| Narrative pronouns | Optional explicit language-tagged forms and grammatical agreement; do not infer from a name; avoid gendered references when absent |
| Tone | Warm, imaginative, reassuring ending; no graphic violence, sexual content, hate, or dangerous instructions |
| Hebrew | Natural modern Hebrew, no niqqud required, RTL metadata, consistent grammatical agreement |
| English | Natural English, LTR metadata, consistent pronouns |

These are starting constraints, not validated educational claims. Developmental profiles guide storytelling rather than diagnose ability or prescribe milestones. Word counts are an engineering length proxy, not equivalent reading difficulty across languages.

## Proposed developmental profiles

All ranges below are initial product hypotheses requiring adult read-aloud trials and bilingual evaluation, not scientifically validated standards. Month intervals are lower-inclusive and upper-exclusive. Profile selection uses age only as a starting signal, not evidence of an individual child's ability. Configuration is maintained separately from graph logic.

| Profile | Months | Experience and narrative strategy | Vocabulary and sentence target | Repetition | Page / word targets |
| --- | --- | --- | --- | --- | --- |
| Newborn | 0–3 | Adult read-aloud; soothing sensory moments and closeness; no conflict or plot requirement | Familiar people, sounds, touch; 2–5 words per utterance | A short refrain on each page | 4 pages; 5–15 words/page; 20–60 total |
| Infant | 3–12 | Adult read-aloud; gentle noticing and predictable sequences | Concrete familiar objects/actions; 2–6 words/sentence | Recurring sound or phrase | 4 pages; 10–20 words/page; 40–80 total |
| Toddler | 12–36 | Adult read-aloud; familiar routine, simple action and reassuring closure | Concrete nouns and verbs; 3–8 words/sentence | Refrain or repeated action | 5 pages; 15–30 words/page; 75–150 total |
| Preschool | 36–72 | Shared read-aloud; simple goal, gentle obstacle, resolution | Familiar vocabulary with contextual new words; 5–12 words/sentence | Optional recurring phrase | 6 pages; 25–45 words/page; 150–270 total |
| Older child (provisional fallback) | 72 onward | Adult/shared reading by default; connected scenes, character goal, choices and resolution; independent reading is not inferred from age | Richer contextual vocabulary; 8–18 words/sentence | Optional thematic recurrence | 6 pages; 40–70 words/page; 240–420 total |

The open-ended final profile ensures coverage without an invented upper age cutoff; it does not assert one strategy suits every older child. Splitting it into additional bands is an open product decision. Sentence length, vocabulary, repetition and developmental guidance are soft targets. Page/word ranges are approved as configurable hard output checks; they remain product hypotheses and may be revised. Counts exclude titles and use whitespace-delimited words initially in both languages. Configurations may provide separate Hebrew/English targets after evaluation.

## Non-goals

Templates, freeform editing, illustrations, accounts, persistence, payments, printing, PDF layout, streaming, background jobs, RAG, tools acting on external systems, and dynamic supervisor agents. Do not add databases, queues, microservices, or hosting infrastructure for this MVP.

## Acceptance criteria

- Invalid shape or unsupported values produce HTTP 422 and zero provider calls. Locally detected unsafe briefs produce a typed policy rejection before generation.
- `age_months: 0` is valid; negative, fractional, boolean, missing, or coerced string ages are rejected. No unapproved upper age cutoff is introduced.
- Successful output has a title and ordered pages matching the resolved profile's page/word constraints, preserves the child's display name, and includes language, direction, profile ID, and profile version metadata.
- Both language paths cover newborns, infants, toddlers, preschool children, and older children, including band boundaries, malformed outputs, pronoun handling, and quality rejection.
- Only quality-approved stories receive HTTP 200. Schema, provider, budget, or quality failures have stable machine-readable codes and a request ID.
- Normal generation uses two provider attempts; all recovery combined permits at most three attempts. Every attempt is recorded, including failed attempts with unknown usage.
- Tests run without credentials, network access, or paid calls.
- A reviewed bilingual evaluation set covers profile fit, adult read-aloud experience, narrative coherence appropriate to the profile (including plot-free baby stories), personalization, grammar, and safety. Automated success alone does not establish literary quality or safety.

## Open decisions

Milestone 2 implements pure normalization and deterministic quality assessment; see [implemented rules and limitations](VALIDATION_AND_QUALITY.md). Insufficient script evidence is an explicit non-blocking observation, including zero eligible letters. Overall deterministic acceptance is permitted if hard checks pass, without claiming language verification or safety. Milestone 3 executes the bounded graph with scripted fake outputs only; real-model story generation and HTTP behavior remain future work.

- Evaluate and refine the approved provisional band boundaries, page/word and sentence targets, repetition strategies, and language-specific overrides through Hebrew/English review and read-aloud evaluation.
- Decide whether/where to split the open-ended older-child profile and whether to introduce an explicit upper audience age; no upper limit is assumed meanwhile.
- Decide future adult-selected reading preferences/ability overrides; MVP uses the age profile and does not assume independent reading. Curated pronoun presets, additional Hebrew agreement forms and linguistic handling of absent pronouns remain to be evaluated; Milestone 1 accepts explicit forms without inferring them or claiming linguistic validation.
- Select an initial provider/model and approve token prices and per-request cost ceiling after a small bilingual evaluation.
- Decide the release threshold for human evaluation and the intended adult-facing safety wording.
- Public deployment, authentication, abuse controls, retention, and applicable privacy obligations need a separate release decision. MVP assumes local or controlled evaluation access.
