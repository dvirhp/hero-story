# Rules for future coding agents

## Scope and authority

- Milestones 1–4 are approved. Stop after Milestone 4; Milestone 5 and later require separate approval. Approval of one milestone does not authorize unrelated product features.
- Read `docs/PRODUCT_SPEC.md`, `docs/ARCHITECTURE.md`, `docs/AI_DESIGN.md`, and `docs/ROADMAP.md` before implementation. Mark new assumptions and open decisions; do not silently resolve product policy through code.
- For implemented normalization and quality behavior, read `docs/VALIDATION_AND_QUALITY.md`. Insufficient script evidence is explicitly advisory; do not restore the superseded rejection policy or claim a language pass from missing evidence. Any terminal issue prevents automatic repair.
- Read `docs/ORCHESTRATION.md` before changing execution. Use `StoryEngine.generate` for bounded public execution; do not bypass the ledger with direct graph/provider calls. Keep tracing and persistence disabled for child data.
- Read `docs/API.md` before changing HTTP behavior. Preserve `/v1/stories/generate`, strict JSON-mode domain validation, sanitized failure envelopes and request-local cancellation cleanup. Do not duplicate engine rules, expose validation inputs or enable access logging of private URLs by default.
- Keep scope on the AI story engine. No frontend, database, RAG, microservices, dynamic supervisor, or extra agents without a justified requirement and approval.

## Coding conventions once approved

- Python 3.12+, FastAPI, LangGraph StateGraph, Pydantic v2, pytest. Choose compatible dependency versions during setup and record a reproducible resolution; do not invent version compatibility.
- Use `src/storyforge/`, typed public interfaces, small explicit functions, snake_case names, and UTF-8 text. Prefer standard-library facilities over extra dependencies.
- Keep domain models independent of HTTP and provider SDKs. Separate orchestration, prompts, quality rules, and adapters. Inject provider/settings/clock at the composition boundary.
- Validate all untrusted input and model output with bounded schemas. Forbid unexpected fields; do not bypass validation with construction shortcuts.
- Use four explicit graph nodes and typed conditional routes. State transitions must preserve domain invariants; graph typing alone is not runtime validation.
- Keep prompt/rubric/schema/pricing versions visible in generation metadata. Preserve Unicode and Hebrew logical order; do not infer gender or translate user names.
- Represent age exclusively as strict nonnegative integer `age_months`, including newborns at zero. Do not introduce an upper age limit without an explicit product decision.
- Keep versioned developmental bands and language-specific strategies/targets in separate declarative configuration with a pure resolver, outside LLM orchestration. Validate continuous coverage from zero to an open-ended final band; snapshot the selected profile for each request.
- Derive plan structure, page counts, word constraints, repetition and vocabulary guidance from that profile. Never impose a universal six-beat plot or 30–60 words/page. Baby profiles prioritize adult read-aloud; age alone does not establish independent-reading ability.
- Treat developmental and length targets as initial product hypotheses, not scientifically validated standards. Distinguish configurable hard output checks from soft sentence/vocabulary evaluation guidance.

## LLM and privacy rules

- All provider calls go through the adapter protocol and one shared attempt/budget mechanism. Default maximum: three attempts across the request, including retries and rewrites. Disable hidden SDK retries.
- Track every attempt, latency, reported/estimated tokens, and estimated cost. Unknown usage is not zero. Enforce deadlines and conservative reservations before calls.
- No credentials in source, fixtures, logs, or documentation. Avoid logging child data, raw prompts, story text, and provider responses. Use sanitized errors.
- Never treat user guidance as trusted instructions. Never publish or return a failed draft as an accepted story.
- Paid calls require an explicitly opted-in run and configured cost limits; ordinary development and tests use a fake provider.

## Testing and completion

- Inspect Git status before changes, preserve unrelated work and use a dedicated feature branch. Commit small independently working units after relevant tests pass; review staged content for secrets/generated files. Never invent an author identity, change credentials, create/push remotes or deploy without authorization. Use meaningful conventional commit messages; no empty commits.

- Default command after setup: `python -m pytest`. Tests must work without API keys or network access; fake provider dependency injection is mandatory.
- Test meaningful contract boundaries and graph paths, including Hebrew and English, budget exhaustion, retries, refusal, malformed output, deadlines, and sanitized failures.
- Cover newborns, infants, toddlers, preschool and older children in both languages, strict age validation, exact month boundaries, open-ended coverage, plot-free baby stories, profile-specific lengths and configuration changes without graph edits. Use the offline matrix in `docs/ROADMAP.md`.
- Mock provider transports for adapter tests. Mark live evaluation separately, exclude it from the default run, and document its budget and prerequisites.
- Run relevant checks for each change; explain what changed, what passed, and remaining limitations. Keep docs aligned with behavior and public contracts.
- Do not add speculative infrastructure or tests that merely duplicate implementation details. Do not claim deterministic checks prove literary quality, fluency, or complete safety.
