# StoryForge frontend product experience handoff

Updated: 2026-11-05 (Asia/Jerusalem). This document supersedes the earlier foundation-only handoff. The user explicitly authorized the customer-facing frontend and all three creation journeys. No backend, database, provider, infrastructure, billing or deployment changes are included.

## 1. Status, worktree and commits

Worktree: `C:/Users/dvir3/storyforge-frontend`.
Branch: `feature/storyforge-frontend-foundation`.
Previous foundation: `d961b6f9a1061bf8083e3a2c9ec58e119ce9c112`; documentation/base for this iteration: `c2b72c2`.
Current product-experience implementation commit: recorded after final verification below. A subsequent documentation-only commit records its exact hash (a commit cannot include its own hash).

The original StoryForge checkout at `C:/Users/dvir3/OneDrive/Desktop/heroStory` and the persistence/QA worktrees were inspected read-only. No merge or cherry-pick of another agent's branch. The starting workspace `conversation-dashboard` remains unrelated and untouched.

Implemented a navigable interactive product demonstration: colorful storefront, filtered catalog, original illustrated product details, schema-driven template personalization, a reviewed AI brief wizard, manual book studio, shared reader, local book library and supporting pages. All data and save operations are local to the current tab's React memory; refreshing/closing loses books and drafts. The HTTP generation adapter remains disconnected. No AI calls, image generation, purchases, uploads, accounts, cloud writes, push or deployment.

## 2. Confirmed three creation methods

Initial search covered README, product/architecture/roadmap/AI/API/page-count docs, repository notes and the other available StoryForge checkouts. The original three definitions were absent. Clarification was requested immediately while independent shared work continued.

The authoritative definitions were then supplied directly by the user in this conversation on 2026-11-05, titled **StoryForge AI — Confirmed Three Book-Creation Methods**:

| Canonical method | Customer label | Implemented journey |
| --- | --- | --- |
| `AI_GENERATED` | Create with AI / יצירה בעזרת AI | Child details -> story idea/type -> explicit length/density/optional ordered targets -> review -> cancellable local sample -> cover/reader -> explicit Save to my books. Preserves `/v2/stories/generate` integration seam; no real generation. |
| `TEMPLATE_BASED` | Personalize a Book / התאמה אישית של ספר מוכן | Discover -> product detail/sample pages -> dynamic fields from that template's typed schema -> live cover/inside preview -> save local personalized Book -> reader/library reopening. No AI. |
| `MANUAL` | Create Your Own / יצירת ספר בעצמי | Blank book -> title/language/optional child -> add/edit/remove/reorder pages -> layouts/colors/original illustrations -> reader preview -> save draft -> reopen/continue -> finalize -> read. No AI or backend writes. |

All three produce the shared versioned frontend `Book`/`BookPage` view model. Their processes and metadata remain distinct. This is a frontend contract proposal awaiting Agent 3's future canonical HTTP schemas, not a claim that corresponding backend endpoints exist.

## 3. Research, art direction and design system

Studied the requested references for experience quality:

- [Wonderbly homepage](https://www.wonderbly.com/): product-led introduction, prominent book imagery, emotional personalization and a short how-it-works explanation.
- [Kids catalog](https://www.wonderbly.com/personalized-books/kids): theme/age discovery and clear product grouping for adult shoppers.
- [ABC product page](https://www.wonderbly.com/personalized-products/abc-for-you-book): product information next to personalization, previews and contextual FAQs.

Those patterns informed hierarchy and discoverability, not copying. No Wonderbly artwork, product text, brand assets, customer claims, testimonials, prices or exact layouts are included. The resulting identity uses a cream paper base, forest/lagoon ink, coral AI cards, mint template cards, lavender authoring cards, sunshine highlights and sky-blue discovery. Themes reuse a small intentional palette. Dark text, focus rings, contrast checks, rounded cards, restrained hover motion and reduced-motion overrides support readability.

Typography uses system Segoe UI/Arial for controls and Hebrew; Georgia for English editorial headings and covers. No external fonts/assets/analytics requests. Original decorative stars and layered covers give depth without introducing decorative application features.

Six original SVG scenes were authored as code in `frontend/public/art/`: flying whale/explorer, sleepy fox/moon, letter garden, small superhero, family bears and moonlight garden. A seventh asset, `hero-striped.svg`, is the superhero outfit variant; choosing the striped outfit updates both the live artwork and pre-authored prose. No AI image tool or live AI call was used. Artwork attribution/source is recorded in `public/art/README.md`. Images are curated demonstration illustrations; AI samples deliberately have no fabricated generated illustrations.

## 4. Routes, components and state

React 19 + strict TypeScript 6 + Vite 8. React and ReactDOM remain the only production dependencies. No routing/state/i18n framework was added. Vitest, Testing Library/jsdom, Playwright and axe are dev-only. Exact dependencies are pinned by the npm lockfile; Node 22.12+ required, verified on 22.16.0.

Hash routing uses `useSyncExternalStore`, native anchors and browser history. No server rewrite is needed. Unknown routes and missing memory-only book IDs have recovery views. Entered child details never appear in URLs. Hashes contain only route names, catalog IDs and local UUIDs.

| Route | Screen / key implementation |
| --- | --- |
| `#/` | `pages/Home.tsx`: book hero, three distinct creation cards, category links, featured books, age discovery, live name showcase and how it works. |
| `#/books` | `pages/Discover.tsx`: category/search/age/language filters; empty/reset state. Optional `?category=` and `?age=` entry filters. |
| `#/books/:id` | `pages/Product.tsx`: original illustrated cover, description, reading guidance, sample-page carousel, personalize and reader links. |
| `#/personalize/:id` | `pages/Personalize.tsx`: dynamically renders each template's typed field schema and live book preview. |
| `#/create/ai` | `components/StoryForm.tsx`: four-step brief with per-step validation and explicit review/confirmation. |
| `#/generating` | Cancellable sample preparation; only actual local pending state enables the loader. Brief ingredients are explicitly not backend progress. |
| `#/generation-error` | Sanitized friendly error, retained brief and retry-by-user recovery. |
| `#/studio/new` | Creates a local manual Book UUID, replaces route with `#/studio/:id`. |
| `#/studio/:id` | `pages/Studio.tsx`: page thumbnails, editor, layout/color/illustration controls, reordering, draft save, preview and finalize. |
| `#/read/:id` | `components/StoryReader.tsx`: cover, shared `BookSpread`, page controls, reading progress, story lang/dir, keyboard navigation. |
| `#/read/sample-:templateId-:language` | Deterministic catalog sample reader, available on fresh load without a saved library entry. |
| `#/my-books` | `pages/Library.tsx`: in-memory books, created dates, ready/draft/failed filters, reopening and two-action local removal. |
| `#/about`, `#/help`, `#/privacy` | `pages/Info.tsx`: original product story, native disclosure FAQs, accurate demo privacy explanation. |

`src/domain/book.ts` defines frontend schema version `1`: method, UUID, language, title, timestamps, status, cover/cover color, child display name and ordered pages. Pages contain stable IDs, one-based numbers, sentence units, optional educational target ID, optional original illustration, layout and background. AI adaptation preserves educational target assignments. Template books retain template ID/version/values. AI books retain source generation schema/profile metadata. The shared model does not fabricate provider usage or quality approval.

`src/domain/brief.ts` remains pure v2 conversion/validation. Exact decimal arithmetic converts years to integer months with no rounding. Zero months is valid; no product age ceiling. Numbers outside JS safe-integer representation are rejected. Page count is never derived from age.

`src/data/catalog.ts` defines six local, versioned, bilingual book templates. The `TemplateField` discriminated union supports bounded text, textarea and choice fields, with per-template definitions and allowlisted choices. For example, the whale book has a companion; superhero has an outfit detail; other books have different combinations of dedication/cover color. Personalization substitutes names and selected details in pre-authored prose and can prepend a dedication page. These deterministic operations require no AI. The UI does not claim a universal template schema or purchasable inventory.

`hooks/useLibrary.ts` owns local cloned Book snapshots. `hooks/useStory.ts` owns abort/stale-result/unmount protection. `routing/router.ts` owns explicit path parsing/history subscription. App is the composition boundary and coordinates transient previews, one working manual buffer and saved memory snapshots.

## 5. Completed behavior and accessibility

- Responsive storefront and navigation with a mobile disclosure menu, Escape close/focus return, semantic anchors and product/support footer.
- Theme and age discovery. Ages are suggestions for adult shared reading, not educational certification or page-count rules.
- AI wizard fields: preserved child name, exact months/years, independent story language, theme, guidance, type, explicit pages (initial 1–32), density and optional ordered targets. Alphabet mode requires unique letter labels and one target per page. Review exposes normalized months, pages and every supplied brief detail before a request.
- Loading reflects one actual local promise; cancellation aborts it and late results cannot replace the current screen. HTTP retries are absent. Error recovery retains the brief.
- Templates validate required fields and allowed choices, offer instant cover/text preview, save a real local personalized Book and can be read again from the shelf.
- Manual studio supports 1–32 pages in this demonstration, stable-ID reordering, minimum-one-page protection, title/language/child, prose editing, three layouts, five page colors, original illustration choices, preview without finalizing, incomplete draft saves, reopening, and finalization only when every page has text and a title exists. Refresh/close warns after unsaved edits; explicit tab-memory limitations remain visible.
- Reader shows a cover before prose, renders text nodes rather than HTML, separates text/illustration, uses sentence units, disables end controls and shows reading progress. Arrow keys follow the book's own direction, independent of the interface locale. Buttons remain available on mobile; swiping is not implemented.
- HTML lang/dir follow interface language; book regions follow the story language. Native Hebrew logical order is preserved. Type-checked bilingual dictionaries live in `i18n/locales.ts` and `i18n/product.ts`. Current generation capability remains en/he; new languages need reviewed backend support and UI dictionaries, not only an option.
- Skip link, focus on route/step changes (without stealing initial-load focus), native labels/fieldsets, required/invalid semantics, described validation errors, live announcements, keyboard controls and reduced-motion support are implemented. Browser axe checks are basic automated evidence, not a full accessibility or native-language review.

## 6. Actual v2 API contract and mock boundary

Preserved `src/api/contracts.ts`, `client.ts`, `mock.ts`. Inspected actual contracts at base backend `5ae24e9`:
`domain/base.py`, `story.py`, `story_v2.py`, `generation.py`, `generation_v2.py`, `development/v2.py`, `api/routes_v2.py`; and API/page-count/product/quality docs. No backend file was modified.

POST `/v2/stories/generate`, strict JSON, no `/api` prefix or provider/model selection fields:

| Field | Actual contract / frontend |
| --- | --- |
| `schema_version` | Literal string `2`, explicit. |
| `display_name` | 1–40 Unicode code points, non-whitespace. Preserved; no gender inference. |
| `age_months` | Strict nonnegative integer including newborn zero; no backend age ceiling. |
| `language` | Currently `en` or `he`. |
| `theme`, `guidance` | Theme required 1–120; guidance optional 1–500 if supplied. |
| `page_count` | Required positive integer; PagePolicy initial service bounds 1–32, configurable by backend. No age-derived count, clamping or automatic mode. |
| `story_type` | general / bedtime / adventure / educational / alphabet. |
| `text_density` | light / standard. Backend developmental profile determines per-page ranges. |
| `structure` | Optional ordered_targets; exactly one target per page with unique IDs; alphabet requires unique letter labels. Optional base/example metadata and min/max sentence-unit constraints exist but are not yet exposed by the simple target editor. |
| other optional fields | Backend accepts interests, explicit language-tagged pronouns and requested_title. Their types remain present; advanced UI is deferred. |

Success envelope: status, request_id, usage, total_latency_seconds, story, quality and resolved_constraints. Story has schema `2`, title, language/direction, profile ID/version, page_count and ordered pages. A wire page has page_id, page_number, nullable target_id and nonempty sentence_units. **No wire text field**; joined text is derived.

Failure envelope: status failure, request/accounting fields, error code/stage/retryable/safe message, nullable quality; no accepted story. Handles INPUT_INVALID, POLICY_REJECTED, QUALITY_REJECTED, provider availability/refusal/schema, budgets, deadline, configuration and cancellation. The existing client validates consumed approval/page/count/direction/order/target/text fields, handles non-JSON/network failures and hides diagnostics. It is not a complete duplicate runtime backend quality validator. Transport has no automatic retries, uses no-store/omit credentials and passes AbortSignal.

The App constructs only the mock service; no environment flag can silently enable a provider. Service injection exists for tests and a later reviewed composition change. The default AI mock honors name, language, page count and target IDs only. Its six original editorial passages repeat for longer books and truncate for shorter books. It does not honor theme, developmental suitability, density or educational semantics; the wizard review explicitly explains that limit. No fabricated quality approval or provider accounting.

Template catalog, personalization, manual drafts, library and saves are genuine frontend interactions over local data, **not** backend API integration or cloud persistence. The template/manual Book schema is independent from StoryV2 because manual content must not invent age profiles or AI acceptance.

## 7. Agent 3 integration dependencies

Read `C:/Users/dvir3/storyforge-persistence/docs/PERSISTENCE_HANDOFF.md` on the isolated persistence branch (observed tip `73ac933`) without changing it. It describes repository lifecycle and saved AI-story tables, not a public library/template/manual HTTP contract. Its saved pages already preserve ordered sentence units and stable page IDs. It explicitly has no public read/list endpoints or ownership model and proposes separately approved endpoint design. This frontend makes no unauthenticated reads or invented owner IDs.

Required next integration work:

1. Reconcile Agent 1's settled public diagnostic envelope without exposing private diagnostics. Keep generation through the existing bounded v2 engine.
2. Agree with Agent 3 on a canonical three-method Book/BookPage DTO, versioning, method-specific metadata, template versions and field schemas, manual draft/finalization semantics and artwork references. The frontend view model is explicitly provisional.
3. Define authenticated ownership/list/read/save/update/delete endpoints, pagination, retention/deletion and concurrency/revision behavior. Repository UUIDs alone are not ownership.
4. Decide a capability contract for supported languages and configured page limits; current frontend mirrors initial 1–32 bounds. Server remains authoritative; never silently alter an adult's requested count.
5. Decide same-origin development routing/proxy and deployment origin policy. No backend CORS/proxy configuration was edited.
6. Only after explicit reviewed integration, inject the HTTP service against a **confirmed fake-only** server, test v2 response adaptation, cancellation and failure recovery, and then implement separate catalog/template/manual/library adapters. Do not accidentally send existing details to a real provider.
7. Replace demo banners, statuses and copy only when those capabilities actually work; replace memory-only save wording only after ownership/persistence is integrated and verified. Resolve HTTP-success/persistence-failure semantics without retrying generation.

No real backend E2E integration has been executed or claimed.

## 8. Commands and verification

From worktree root, `cd frontend`:

```powershell
npm ci
npm run dev
npm test
npm run build
npm run preview
# Browser setup if Chromium is not already installed:
npx playwright install chromium
npm run test:e2e
```

Browser tests use an owned production-preview server on `127.0.0.1:5186`, desktop and mobile Chromium profiles, no external requests/API calls, workflow assertions, axe checks and screenshots. A pre-existing local Chromium may be selected with `$env:STORYFORGE_CHROMIUM_PATH = '<absolute chrome executable>'`. Test output/traces are ignored. Stop Vite before npm ci on Windows to avoid a locked native dependency.

Final verification on 2026-11-05:

- **74 unit/component tests passed** in four files. Covers all three workflows, per-step validation and review, newborns and exact month conversion, page policy boundaries independent of age, ordered targets preserved through the Book adapter, dynamic template schemas and allowlisted choices, literal user text, outfit artwork/prose changes, manual finalization/reordering/stable IDs, routing, reader bounds, language direction, cancellation/stale responses, error recovery and mocked HTTP validation. The existing HTTP client and its original boundary tests remain unchanged.
- **12 Playwright tests passed** (six desktop + six mobile) against the production build in Chromium. All three creation workflows were exercised in English and Hebrew, including a newborn, three-page English alphabet request and a one-page Hebrew AI sample; explicit save/reopen, draft editing, reorder/remove, layouts/colors/art, preview/finalize, reader boundaries, RTL arrow keys and independent interface/story directions.
- Browser checks also cover catalog filtering/empty recovery, product sample pages, native back navigation, unknown routes, missing books, help/error pages, skip-link keyboard focus, mobile menu Escape/focus return, route overflow sweeps and extra 320/768/1024 px checks. Project viewports: 1440×1000 desktop and 390×664 mobile (iPhone 13 profile, DPR 1 for compact review screenshots).
- All axe WCAG 2 A/AA and 2.1 A/AA checks invoked by the browser suite returned **zero violations**. These cover home, catalog, product, AI review/reader, personalization, library, studio, Hebrew reader and error views in both projects. No blanket accessibility certification is claimed. Confirmed contrast, accessible-label, initial-focus and mobile Escape defects found during testing were corrected.
- Every browser journey asserted **zero browser exceptions, zero attempted external requests and zero attempted v2 API calls**. Request interception aborts unexpected external/API calls before transport. No backend E2E or provider success is claimed.
- **Production build passed**, including strict TypeScript. Main JS 314.80 kB / 97.62 kB gzip; CSS 41.56 kB / 9.52 kB gzip. The final route-typing cleanup emits the same runtime bundle as the browser-tested build.
- `npm install` audited 109 packages with zero reported vulnerabilities after adding the dev-only browser/accessibility tools. The lockfile is tracked. Pre-existing local Chromium was used via `STORYFORGE_CHROMIUM_PATH`; no browser was downloaded for these checks.
- **22 actual desktop/mobile screenshots** captured and visually inspected for representative home, personalization, studio and Hebrew reader pages. Browser traces/reports, installed dependencies and production outputs remain ignored.
- Source formatted with Prettier; Git whitespace/scope review performed. No backend tests were changed or rerun for this frontend-only iteration.

## 9. Screenshots

Tracked review artifacts in `docs/frontend-screenshots/` are captured from the actual rendered application by the Playwright suite, using synthetic names and original artwork:

- `home-desktop.png`, `home-mobile.png`: storefront and three methods.
- `catalog-desktop.png`, `catalog-mobile.png`: discovery.
- `product-desktop.png`, `product-mobile.png`: product and sample pages.
- `personalize-desktop.png`, `personalize-mobile.png`: dynamic template fields/live inside preview.
- `ai-review-desktop.png`, `ai-review-mobile.png`: reviewed newborn brief, explicit three pages.
- `ai-reader-desktop.png`, `ai-reader-mobile.png`: mock-generated prose.
- `studio-desktop.png`, `studio-mobile.png`: actual edited/reordered pages and controls.
- `manual-reader-desktop.png`, `manual-reader-mobile.png`: assembled manual book.
- `hebrew-reader-desktop.png`, `hebrew-reader-mobile.png`: Hebrew book and interface.
- `library-desktop.png`, `library-mobile.png`: saved local template book and preloaded shelf.
- `help-desktop.png`, `help-mobile.png`: support page.

These are review screenshots, not static mockup substitutes. The source application and functional tests are delivered alongside them.

## 10. Changed files and known limits

All changes are restricted to `frontend/`, this document and `docs/frontend-screenshots/`. The exact manifest is available with `git diff --name-only c2b72c2 HEAD` after commit.

Changed existing: `frontend/README.md`, `.gitignore`, package/lock, Vite test config, App, StoryForm, StoryReader, useStory, brief defaults and stylesheet. The original typed v2 client and boundary tests remain intact.
Added: BookCover, BookCard, BookSpread; Home/Discover/Product/Personalize/Library/Studio/Info pages; canonical book domain; catalog/schema fixtures; product dictionaries; memory-library hook; hash router; domain tests; updated journey component tests; Playwright configuration/specs and original SVG assets.

Known limits / unfinished integration:

- No backend requests, authenticated ownership, permanent storage, real template inventory, manual APIs, uploads, image generation, PDF/print, payments or deployments.
- A tab refresh resets the shelf to synthetic fixtures. Only one unsaved manual working buffer is held; explicitly save drafts before starting a different book. A completed AI preview is also transient until saved. This is not crash recovery or browser storage.
- Manual editor demonstrates 1–32 pages and basic bounded text/layouts; no rich text, undo history, asset upload or real print-pagination engine. Saved drafts can be incomplete; finalized text is author-written and not claimed AI-quality-approved.
- Six original art scenes are reused across template pages. Template educational copy is original illustrative prose, not a validated teaching program. Age ranges and density are provisional guidance, not scientific claims.
- The simple AI target editor does not expose final-form base/example metadata, explicit pronouns, requested titles or sentence-unit ranges; no claim of the complete Roy workflow.
- Catalog language/age discovery uses local fixtures. Page limits/languages need a future server capability contract. Additional language support requires reviewed content and backend contracts.
- Product deep links work for local catalog samples; library/manual UUID deep links require that book in current-tab memory.
- Basic automated accessibility and Chromium checks do not establish exhaustive assistive-technology coverage, other-browser compatibility, literary quality, developmental suitability or native-language fluency.

Stop for review after delivery. No live AI calls, push, merge or deployment are authorized by this work.
