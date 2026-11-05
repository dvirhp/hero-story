# StoryForge frontend handoff

Updated: 2026-11-05. This frontend work is explicitly authorized by the user's Agent 2 brief, superseding the historical no-frontend scope in AGENTS.md for this task only. Backend milestones, paid requests and deployment remain outside scope.

## Status and location

The supplied working directory (`C:/Users/dvir3/conversation-dashboard`) was an unrelated Angular/Go application. Inspection located StoryForge in `C:/Users/dvir3/OneDrive/Desktop/heroStory`, with no existing frontend. Agent 1 had uncommitted Gemini diagnostic work there. No files in that checkout were changed.

Dedicated Git worktree: `C:/Users/dvir3/storyforge-frontend`.
Branch: `feature/storyforge-frontend-foundation`.
Base commit: `5ae24e9` (`docs: document v2 migration and approval-gated Roy test requirements`).
Implementation commit: see `git log -1 --format="%H %s" -- frontend` for the exact commit containing this handoff and implementation. A commit cannot include its own hash. Delivery will report that hash; later documentation-only commits do not change the implementation identity.

Implemented local foundation; ready for review, with HTTP integration deliberately inactive. No pushes, merges, cherry-picks, deployments, backend changes or real AI calls.

## Architecture and files

React 19 + TypeScript 6 (strict) + Vite 8; React/ReactDOM are the only production dependencies. Vitest 5, Testing Library and jsdom provide frontend tests. Exact versions are pinned in `frontend/package-lock.json`. Node 22.12+; validated using Node 22.16.0/npm 10.9.2. The original npm peer resolver failed while resolving Vitest 4 optional peers; explicitly selecting compatible Vitest 5 resolved it. No legacy-peer or force-install flags were used.

All added/modified files are within `frontend/` and this document:

- `frontend/package.json`, `package-lock.json`: commands, dependencies and reproducible lock.
- `frontend/.gitignore`: excludes installed dependencies, build outputs, TS build info and local environment files.
- `frontend/index.html`, `tsconfig.json`, `vite.config.ts`: standalone Vite entry, compiler and test configuration.
- `frontend/README.md`: developer startup and integration warning.
- `frontend/src/main.tsx`, `vite-env.d.ts`: React entry and Vite type declarations.
- `frontend/src/App.tsx`: application composition, screen rendering, locale, in-memory brief, focus management.
- `frontend/src/styles.css`: responsive design, logical CSS properties, reduced motion and focus styles.
- `frontend/src/components/GardenArt.tsx`: decorative inline SVG; no story illustrations or image generation.
- `frontend/src/components/StoryForm.tsx`: reusable field presentation, sections, validation and brief summary.
- `frontend/src/components/StoryReader.tsx`: approved-story view model, sentence-unit rendering and bounded page navigation.
- `frontend/src/domain/brief.ts`: pure validation and v2 payload conversion, exact decimal age-to-month arithmetic.
- `frontend/src/hooks/useStory.ts`: injected service, screen state, request cancellation, unmount cleanup and stale-result protection.
- `frontend/src/i18n/locales.ts`: typed English/Hebrew dictionaries, locale/direction registry and story-type labels.
- `frontend/src/api/contracts.ts`: v2 request, story, success/failure, quality and accounting types.
- `frontend/src/api/client.ts`: optional typed HTTP service, safe errors, consumed-response validation; never selected by the app.
- `frontend/src/api/mock.ts`: delayed, abortable local editorial samples.
- `frontend/tests/brief.test.ts`, `client.test.ts`, `app.test.tsx`: contract boundary, transport and interaction tests.

State is React state with service injection rather than a new framework. No localStorage, telemetry, external fonts, external artwork, cookies, database, auth, payments, image generation or PDF export. Routes are in-memory screens: reload returns to the landing page.

## Completed screens and behavior

1. Landing: product introduction, three feature explanations, create CTA and bilingual sample reader.
2. Creation: child name; years/months; independent story language; theme; optional guidance; five story types; explicit 1–32 pages; light/standard density; optional ordered learning targets; alphabet mode requires unique letter labels. Live sidebar summary on wider screens.
3. Loading: clearly labeled local demo, friendly progress wording and cancellation; no invented backend progress events or percentage.
4. Reader: title, sentence units joined by presentation, numbered pages, disabled end controls, mixed UI/story directions and create-another action.
5. Error and empty states: friendly recovery paths, retained brief on error, explicit demo-state controls in footer.

Interface language is independent from story language. HTML lang/dir follow interface locale; reader lang/dir follow story metadata. Hebrew is kept in logical Unicode order. Logical spacing/layout, native labeled controls, semantic fieldsets, visible focus, skip link, live announcements, invalid-field focus, keyboard-accessible controls and reduced-motion support are included. Generation language enum remains the backend's current en/he contract. Future locales require reviewed dictionaries plus backend support before generation is exposed; adding an option alone is insufficient.

## Actual backend contracts

Inspected from the base commit, not invented from the brief:

- `src/storyforge/domain/base.py`, `story.py`, `story_v2.py`, `generation.py`, `generation_v2.py`.
- `src/storyforge/development/v2.py`, `src/storyforge/api/routes_v2.py`.
- `docs/API.md`, `PAGE_COUNT_V2.md`, `PRODUCT_SPEC.md`, `ARCHITECTURE.md`, `AI_DESIGN.md`, `ROADMAP.md`, `VALIDATION_AND_QUALITY.md`.

POST `/v2/stories/generate`, JSON body. No `/api` prefix or provider/model fields. Strict backend forbids extra fields.

| Field | Contract / frontend behavior |
| --- | --- |
| `schema_version` | Literal string `"2"`; sent explicitly. |
| `display_name` | 1–40 Unicode code points, non-whitespace. Original supplied name preserved; no gender inference. |
| `age_months` | Strict nonnegative integer including 0; no backend age ceiling. UI accepts months or years only when exact whole months result, including 1.5 years -> 18 months. No rounding. JS safe-integer boundary is a frontend numeric limit. |
| `language` | Currently `en` or `he`. |
| `theme` | 1–120 characters, non-whitespace. |
| `guidance` | Optional/null, 1–500 characters when supplied. Empty UI value omitted. |
| `page_count` | Required positive integer. Configurable PagePolicy initially 1–32; frontend currently mirrors those initial limits. Never inferred from age or silently clamped. |
| `story_type` | `general`, `bedtime`, `adventure`, `educational`, `alphabet`. |
| `text_density` | `light` or `standard`; age controls per-page ranges, never page count. |
| `structure` | Optional `kind: "ordered_targets"`, one target per requested page, unique `target_id`. UI makes stable ordinal IDs and preserves entered label order. |
| target fields | `target_id`, `label` (1–40), `kind: concept/letter`; optional `base_form`, `example_word` exist in backend but advanced editing is deferred. Alphabet requires letter kind and unique labels. |
| other optional fields | Backend supports `interests` (up to five), explicit language-tagged `narrative_pronouns`, `requested_title`, and structure `sentence_units_per_page`. Types preserve these, UI does not expose them yet. |

Success: `status: "success"`, `request_id`, `usage`, `total_latency_seconds`, `story`, `quality`, `resolved_constraints`.
Story: `schema_version: "2"`, `title`, `language`, `direction`, `profile_id`, `profile_version`, `page_count`, ordered `pages`.
Page: `page_id`, `page_number` (one-based), `target_id` (nullable), nonempty `sentence_units` array. **There is no wire `text` field**; backend's page text property is derived. Reader renders sentence units as text nodes, never HTML.
Resolved constraints: page count, per-page/total min/max words, target IDs, optional min/max sentence-unit range, policy version. Quality includes passed, issues, check/rubric versions. Full accounting types are recorded but not displayed to product users.

Failure: `status: "failure"`, same request/accounting envelope, `error` (`code`, `stage`, `retryable`, safe `message`), nullable `quality`; never a story. HTTP statuses include 422 INPUT_INVALID/QUALITY_REJECTED, 400 or 502 POLICY_REJECTED by stage, 502 provider/schema/refusal, 503 availability/budget, 504 deadline, 500 configuration and best-effort 499 cancellation. Client checks discriminant and HTTP status, handles malformed/non-JSON/network failures, performs no retries, and never displays raw diagnostic messages.

The optional client uses `credentials: omit`, `cache: no-store`, an AbortSignal and request-scoped cancellation. It validates consumed success fields (approval, declared count, language/direction, ordered pages, unique IDs, target assignments and sentence units), not every accounting field or all backend quality rules. Backend remains authoritative. Abort does not guarantee already-started remote work is stopped or unbilled.

## Mock versus integration

The default app imports only `createMockStoryService`. It never constructs the HTTP service and has no environment switch that could accidentally enable provider calls.
The mock personalizes the name, selects English/Hebrew prose, returns the requested page count and attaches requested target IDs. It does **not** honor theme, guidance, age density, story type, educational semantics or backend quality policy. Six editorial sample passages cycle for books longer than six pages; shorter books show the first N. This is deliberately labeled a sample, with no fake quality approval or fabricated backend accounting. It is not an accepted generated manuscript or proof of teaching/developmental quality.

The HTTP adapter is implemented and tested using mocked fetch only; no running backend was contacted. No CORS/proxy/backend configuration was changed.

## Commands and checks

From worktree root:

```powershell
cd frontend
npm ci
npm run dev
# open Vite's printed localhost URL
npm test
npm run build
npm run preview
```

`npm test` runs only frontend tests offline, without keys or backend. `npm run build` runs strict TypeScript checks then creates ignored `dist/`. Backend tests were not rerun because no backend files changed.

Final local checks (2026-11-05):

- `npm ci`: passed from the committed lockfile; 103 packages installed, 0 reported vulnerabilities. On Windows the first clean install attempt encountered a locked native Vite dependency while the dev server was running; stopping that owned server and repeating `npm ci` succeeded. Stop Vite before reinstalling dependencies on Windows.
- `npm test`: **40 passed**, 3 files. Covers newborns, exact month conversion/fraction rejection, open-ended ages within JS numeric representation, explicit page bounds independent of age, educational cardinality, Hebrew/Unicode controls, request serialization, safe failures, malformed/unapproved response rejection, navigation boundaries, RTL/LTR independence, invalid-field focus, cancellation/stale results, retained input after service errors and empty states.
- `npm run build`: passed (strict TypeScript and Vite production bundle). Main JS 248.65 kB / 78.68 kB gzip; CSS 11.91 kB / 3.52 kB gzip. No external runtime asset dependencies.
- Headless Chromium checked both Vite dev and final production-preview builds. Landing widths 320/390/768/1440 had no horizontal overflow. Mobile form and Hebrew reader also passed overflow checks. Completed newborn, three-page alphabet mock flow; loading shown; first/last reader controls disabled correctly; switched UI direction independently of existing story direction; read Hebrew sample. **No browser exceptions or external network requests** during the flow. No backend requests were made.
- Visually inspected desktop landing, mobile form and Hebrew reader screenshots. Screenshots and the one-off browser QA script are local review artifacts outside Git at `C:/Users/dvir3/storyforge-*.png` and `C:/Users/dvir3/storyforge-browser-qa.mjs`. Browser QA used pre-existing cached Playwright and Chromium; neither was added as a project dependency. Future CI browser automation is not configured; reproduce the described flow manually with `npm run preview` or establish a pinned browser test setup.
- Source formatting applied with Prettier. Git whitespace check and staged-file scope review performed before commit. Generated output and node_modules excluded. Existing backend files and tests unchanged by this branch.

## Limitations and unresolved decisions

- Desktop/mobile browser checks supplement tests; no screen-reader/manual linguistic review or full accessibility audit claimed.
- Current initial page limits are static frontend policy; no capability endpoint currently supplies deployed limits. Reconcile before integration; do not silently change a requested count after server rejection.
- No URL routing/history, saved library, editing, persistent state, streaming or background jobs. Refresh discards the brief.
- No pronunciation/pronoun presets; omitted pronouns are intentional. Final-form base/example metadata, requested titles, interests and sentence-unit range need reviewed UI designs. The simple alphabet editor does not implement the complete Roy fixture workflow.
- Page count is explicit and mutable only by the adult; no automatic mode. Density guidance is provisional, not a developmental claim.
- Friendly generic generation error intentionally omits raw server detail; code-specific localized recovery and support request-ID presentation can follow integration review.
- The frontend is not a public-service release. Production privacy, authentication, abuse controls and deployment need their own scope.

## Integration after Agent 1

1. Review Agent 1's completed diagnostics changes without merging/cherry-picking them here. Reinspect the settled v2 schemas and failure envelope; update types/tests if the approved public contract changed. Do not expose private diagnostics.
2. Check the final fake-only backend composition and explicit page-policy/model admission limits. Only choose a reviewed fake backend for the first integration; never assume an existing server uses fake.
3. Decide local same-origin routing (development proxy or deployment gateway) and origin policy. There is no frontend proxy now and no backend configuration was edited.
4. In an explicitly reviewed composition change, import `createHttpStoryService` and inject it into `<App service={...}/>` instead of the mock. Remove/adjust demo-only wording and footer previews when appropriate; current App always describes sample behavior.
5. Test JSON v2 success, failure, abort and timeout against a confirmed fake-only server; retain UI validation, server authority, no automatic retry, and safe error handling.
6. Verify count, target metadata, configured density limits and language direction against backend response. Test Hebrew/English/mixed script with adults and native reviewers. Plan reviewed language packs before enabling additional generation languages.
7. Keep provider calls, production persistence/auth/payments, billing and deployment out of this integration unless separately authorized.
