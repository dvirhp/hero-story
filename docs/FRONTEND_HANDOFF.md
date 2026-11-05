# StoryForge premium frontend handoff

Updated 2026-11-05 (Asia/Jerusalem). Supersedes the earlier foundation and three-method handoffs. This is a functional local customer-experience demonstration, **not production commerce or connected AI**. No backend/database/provider changes, live AI, payments, merges, pushes or deployment.

## 1. Worktree, milestones and implementation status

- Worktree: `C:/Users/dvir3/storyforge-frontend`; branch: `feature/storyforge-frontend-foundation`.
- Earlier foundation: `d961b6f`; three-method experience: `1e2a3e6`; reviewed baseline: `1647d71`.
- M1 `bd40358`: ocean/pearl visual identity and physical Hebrew/English reader.
- M2 `a3b221d`: typed template character schemas, original avatar previews, sort and gallery.
- M3 `b09f54b`: formats, bag, complete guest checkout, payment simulation, confirmation/history/detail.
- M4 `e5d4d11`: editor duplication/position/cover/dedication, source-copy editing, opt-in guest recovery, proposed async/session/usage ports.
- M5 and final documentation identifiers are recorded in the delivery section below after verification.

| Status | Delivered behavior |
| --- | --- |
| Functional local frontend | Home, discovery/search/filter/sort, product gallery, schema-driven personalization, deterministic avatar, reader, all three creation journeys, manual draft editing/reopening, cart configuration identity/quantities, guest step validation, discount, payment decline/retry, confirmation/history/detail, consent-controlled refresh recovery. |
| Deterministic mocks | Six versioned bilingual catalog products and static original art; AI sample text; all offers, USD pricing, shipping fees, promo eligibility and payment/order outcomes. No real stock or purchasable inventory. |
| Partial | One manual working buffer, basic text/layout editor, local avatar overlays, reviewed en/he UI only, async observer port with no HTTP implementation. |
| Missing/dependent | Server-owned catalog/books/assets, durable guest/account ownership, sessions/CSRF, async execution/reconnect, enforced quota admission, real offers/tax/shipping/payment/fulfillment, uploads, image pipeline, PDF/print. |

Audit, actual-reference comparison, source links, baseline gaps, implementation order and per-milestone evidence: [FRONTEND_PREMIUM_AUDIT.md](reviews/FRONTEND_PREMIUM_AUDIT.md). Wonderbly, Hooray Heroes and Librio were inspected read-only; no third-party checkout, customer submission, artwork or source code was reused. Client-rendered reference widgets were not exhaustively tested.

## 2. Confirmed creation methods

| Method | Complete local journey | Boundary |
| --- | --- | --- |
| `AI_GENERATED` / Create with AI | Child details, exact months/years, story language, optional local avatar, theme/type/guidance, explicit pages/density/targets, review, cancellable sample, reader, save, edit an independent copy, demo format/cart. | Only supported fields enter StoryRequestV2. Age never selects page count. Avatar does not modify AI illustrations. Local sample is not developmentally/educationally validated. |
| `TEMPLATE_BASED` / Personalize a Book | Catalog -> product -> template-specific fields and avatar options -> immediate cover/text preview -> saved book/reader -> format/cart. | Pre-authored local fixtures with template version and dynamic schema. No universal personalization form or AI call. |
| `MANUAL` / Create Your Own | Blank book -> title/language/optional child -> add/remove/duplicate/reorder pages -> prose/layout/background/original art/position -> cover/dedication -> preview -> save/reopen -> finalize -> format/cart. | Real interactive editor; no upload/cloud/PDF claim. Finalization checks text/title, not AI approval. |

All produce shared frontend `Book`/`BookPage` schema `1`. Method-specific source metadata stays separate. `editableCopy` issues fresh book/page IDs, sets MANUAL/draft, records `editedFrom`, and removes generation/template approval metadata without changing the original. This frontend view model is **not** Agent 3's wire PageDocument.

## 3. Architecture and design

React 19, strict TypeScript 6, Vite 8. React/ReactDOM are the only runtime dependencies. Node >=22.12 (verified 22.16). Native hash routing/history (`useSyncExternalStore`), React hooks for state, pure domain functions, typed services; no unnecessary routing/state/i18n packages. Vitest/Testing Library/jsdom, Playwright and axe are dev dependencies. The lockfile pins actual versions.

- `src/pages/`: home, discovery, product, personalization, library, studio and information screens.
- `src/components/`: BookCover/BookSpread, guided StoryForm, physical StoryReader, quota information.
- `src/personalization/`: typed per-product `CharacterSchema`, visual builder, original deterministic SVG character renderer.
- `src/domain/`: pure brief normalization and versioned Book/Page model, editing helpers/finalization.
- `src/data/catalog.ts`: original versioned bilingual templates, per-template field/character schemas, validation, literal dedication/name substitution.
- `src/commerce/`: pure immutable bag/quote model, offers/payment simulation boundary, cart/format/checkout/orders views and state hook.
- `src/state/tabRecovery.ts`: consent-gated sessionStorage and bounded runtime validation, never an ownership/authentication source.
- `src/api/`: existing v2 contracts/client/mock plus separately documented proposed product ports.
- `src/i18n/`: UI registry, regional-tag resolution/fallback, typed core/product/experience dictionaries, shared copy accessor and Intl formatting.
- `src/routing/router.ts`: allowlisted hash routes and IDs. Child/contact data never goes in URLs.
- `public/art/`: seven original SVG scenes/variant, created as code; no live image generation or copied reference artwork.

Visual system uses deep ocean ink, teal, pearl neutrals and copper/peach accents, with lavender/sky story worlds, script-appropriate system Hebrew/Latin font stacks, logical spacing, rounded controls/cards and reduced-motion overrides. Cover title ink is selected using actual contrast. No external font/asset requests are required. Subtle book-opening transforms mirror the physical hinge for Hebrew.

UI language and book language are independent. `registry.ts` is separate from backend Language. Only en/he are reviewed and selectable; unknown UI tags fall back to English, regional tags to the reviewed base. Adding a UI locale requires dictionaries, metadata, long-string/RTL tests and reviewed content; adding a story language also requires backend capability. Backend catalog locale behavior must not be silently replaced by UI fallback. Prices use Intl with explicitly illustrative USD (no currency conversion); dates use locale formatting with an explicit timezone.

## 4. Routes and reusable screens

| Hash route | Implementation / behavior |
| --- | --- |
| `#/` | Home: editorial book hero, three creation cards, worlds/age discovery, shelves and live name showcase. |
| `#/books` | Discover: search/category/age/language, locale-aware sorting, no-results/reset. Optional category/age query entry filters. |
| `#/books/:id` | Product: cover/inside/character gallery, original copy, sample carousel, personalization and sample reader. |
| `#/personalize/:id` | Dynamic template fields, supported avatar controls, language, cover choices and dedication where allowed; preview and save. |
| `#/create/ai` | Four-step StoryForm; validation/review; independent page count 1-32. |
| `#/generating`, `#/generation-error` | Actual pending local promise/cancellation, safe error and retained-brief recovery. No invented provider percentages. |
| `#/studio/new`, `#/studio/:id` | Studio blank/draft editing; add/remove/duplicate/reorder, text/layout/color/art position, cover/dedication, preview/save/finalize. |
| `#/read/:id` | Shared physical reader, book-language-owned hinge/order/navigation, thumbnails, touch/keys, fullscreen request/error. |
| `#/read/sample-:templateId-:language` | Fresh-load deterministic catalog sample, no saved ownership required. |
| `#/my-books` | Local shelf, status filter, reopen/edit, explicit two-action removal. |
| `#/format/:id` | Demo format radio options, quantity, eligibility, error recovery and add-to-bag. |
| `#/cart` | Immutable configured snapshots, quantities/remove, badge and integer-cent summary. |
| `#/checkout` | Guest contact/address/delivery/review, promo, no-card simulation and decline recovery; empty-bag recovery. |
| `#/confirmation/:id`, `#/orders`, `#/orders/:id` | Simulated confirmation/history/detail, status/summary and missing-order state. |
| `#/about`, `#/help`, `#/privacy` | Brand/help/native disclosures, current storage and commerce limits. Unknown paths have a recovery page. |

Desktop >=900px: opening page 1 faces the inside cover; subsequent spreads pair 2/3, 4/5. Hebrew page 2 is physically right, page 3 left; English is mirrored. Narrow screens show one page. Cover opens from the corresponding hinge. Keyboard, swipe, buttons, indicators and thumbnails follow **book** direction, even if interface language differs. Whole illustrations use contain; intentionally positioned manual art is bounded and retains its position in the reader. Fullscreen depends on browser permission/support; graceful message on rejection. Motion reduces when requested.

## 5. Mock, storage and commerce boundaries

Default state is current-tab React memory. Footer opt-in writes only namespaced `sessionStorage`: consent, locale, library books, current manual working draft, AI brief and bag. Storage has size/schema checks; malformed data is ignored and write failures reported. Withdrawal clears only StoryForge keys. Closing the tab clears session data; browser restore behavior is browser-managed, so this is not a durable backup. Adults should use synthetic data for demonstrations. Character-only AI preferences and in-flight generated previews are not recovered until saved as a book. Checkout contact details, addresses, emails, orders, CSRF tokens and job keys are **never** persisted. No analytics/localStorage/cookies/account service is used.

Catalog products are demonstration content. `demoOffer` explicitly supplies illustrative softcover/hardcover/digital prices (USD 29/39/9), maximum quantity 10, standard/express delivery fees (USD 5/12), STORY10 discount and no tax calculation. These are sample policy, not backend business rules or an offer to sell. Bag identity includes method/content/language/character/cover/template/format, excludes incidental UUIDs/timestamps, and preserves snapshots; identical configurations merge while different configurations/formats remain separate. Eligibility is demo-ready content only.

`PaymentSimulation.run` accepts only an intent, demo quote and decline flag, never card/contact information. It is abortable, deterministic/idempotent by in-memory intent, and can deliberately decline. Orders are labeled simulated/not placed; no charge, stock reservation, printing or shipping occurs. History lasts in React memory only. Real provider integration requires a different reviewed adapter and server-owned quotes/verification.

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

## 7. Agent 1 / Agent 3 integration dependencies

Read Agent 3 documentation read-only in `C:/Users/dvir3/storyforge-persistence`; latest observed tip `b6af124`. `API_CONTRACTS.md` explicitly says Phase A accepted in principle, implementation planning, **no new endpoints/OpenAPI implemented**. Earlier observed planning tip was `7e38326`. No merge/cherry-pick or edits to that worktree.

`src/api/productPorts.ts` models proposal seams, not a shipped HTTP API: session context, independent story/image usage, one intentional async start and read-only operation observation. The async route proposed in Agent 3 docs is POST `/v3/jobs/stories`, 202 + Location/Retry-After; GET operation recovery. State/result details remain provisional until executable contracts are approved. The observer has bounded polling, AbortSignal and no creation retries. A fresh intentional creation gets a 256-bit base64url intent key. No HTTP port is instantiated in App. The visible allowance disclosure says not connected; it never invents remaining credits. A future server response may render independent balances.

Required integration sequence:

1. Agree on actual executable session/CSRF, anonymous ownership, safe error/status and usage contracts with Agent 1/3. Future same-origin guest cookies and memory-only CSRF must be an explicit adapter change; existing disconnected v2 client currently uses `credentials: omit`. No automatic fresh session or creation on 401.
2. Implement an approved async job adapter: one POST per user intent, server-scoped idempotency, GET-only reconnect/status/result, bounded polling/backoff and cancellation semantics. Ambiguous admission must not become another creation. Server policy is proposed 10 story + 10 image creations/day UTC, separate capabilities; committed dispatch consumes, proven pre-dispatch failures release. Never authorize from local counters. Session duration/replay guarantees are server-owned (current proposal: fixed 30 days, terminal replay >=48 hours).
3. Map frontend Book/Page to Agent 3 BookDetail/PageDocument text/image blocks, revision/ETag and asset bindings; do not send frontend scene names, CSS layout metadata or SVG as if they were accepted backend assets. Backend proposal disallows uploaded SVG. Keep AI acceptance/source metadata separate from manual edits.
4. Replace fixtures with catalog/template versions, dynamic field schemas and quota-free template previews. Define migration/locale/validation handling; unsupported fields must stay absent. Resolve asset/illustration pipeline before promising generated character appearance.
5. Add owned library CRUD, guest session recovery/linking, concurrency conflicts, retention/deletion and safe draft synchronization. Account linking UI may become active only after real identity adapters exist. No mandatory signup for discovery/creation.
6. Define server product/format eligibility, inventory, signed quote/pricing/tax/shipping/promo/cart/order/payment/fulfillment contracts. No commerce routes currently exist in inspected proposals. Use approved hosted/provider payment fields; never extend this mock to collect card data.
7. Reconcile Agent 1's public error envelope and quota protection of legacy AI routes; preserve engine-owned page limits, budgets, quality checks and development profiles. Add contract/integration tests with fake providers before any approved live integration. Do not bypass the server by reusing demo rules.

## 8. Commands and verification

From `frontend/`, Node >=22.12 and npm:

```sh
npm ci
npm run dev
npm test
npm run build
npm run preview
npx playwright install chromium
npm run test:e2e
```

Browser installation is a one-time download; ordinary tests use local assets/localhost only. Playwright owns port 5186, with desktop 1440x1000 and emulated iPhone 13 Chromium projects. Set `STORYFORGE_CHROMIUM_PATH` to an installed compatible executable if needed. On this machine the verified path was `C:/Users/dvir3/AppData/Local/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-win64/chrome-headless-shell.exe`. Stop only an identified task-owned preview if port 5186 is already occupied. Dev usually uses 5173. Production assets, dependencies, transient browser reports/traces are ignored. No backend tests were modified or rerun for this frontend-only work.

Verification results and M5 commit are finalized below after the final run. Earlier milestones: M1 75 unit/component +2 focused browser; M2 77+2; M3 87+2; M4 106+2. Build passed at each milestone. Initial broad hardening runs found bag accessible-name spacing; it was fixed and targeted axe verification confirmed the correction before the final full rerun. Reader positioning regression received a browser assertion. Automated checks do not prove full WCAG conformance, native-language quality, developmental suitability or compatibility with Safari/Firefox/real mobile hardware.

## 9. Screenshots and files

Actual Chromium captures in `docs/frontend-screenshots/` (synthetic data, original artwork), not static mockups:

- `home`, `catalog`, `product`, `personalize`, `library`, `help`, `ai-review`, `ai-reader`, `studio`, `manual-reader`, `hebrew-reader`: desktop/mobile complete journeys.
- `reader-premium-{en,he}-{desktop,mobile}`: physical book sides and page overview.
- `character-premium-{desktop,mobile}`: visual avatar/schema controls.
- `cart-premium`, `checkout-premium`, `confirmation-premium`: desktop/mobile guest commerce and decline simulation.
- `editor-refined-{desktop,mobile}`: duplication, art position, cover/dedication and recovery.
- `checkout-hebrew-{desktop,mobile}`, `rtl-wide-{desktop,mobile}`: translated checkout and wide RTL reader.

Changed/created areas for this iteration: `frontend/src/App.tsx`, shared BookCover/BookSpread/StoryReader/StoryForm/QuotaPanel, Home/Discover/Product/Personalize/Studio, book/brief domain, catalog, library hook, routing, styles, i18n dictionaries/registry/accessor, **new personalization/, commerce/, state/tabRecovery.ts, api/productPorts.ts**, tests and browser specs; audit/handoff and screenshots. Runtime dependencies stay React-only. Exact manifest: `git diff --name-status 1647d71 HEAD`. Backend/provider/config/test paths are outside the diff.

## 10. Remaining limitations / review decisions

- This is a polished local frontend, not production-ready selling or connected AI. Real inventory/prices/delivery/account/cloud persistence/quotas/jobs are absent by design.
- Avatar is an original deterministic overlay, not a full scene/AI art pipeline. Six original scenes plus one outfit variant are reused. No asset upload, generated art, PDF or print proof.
- Basic bounded editor: no rich text, undo history, crop tool, arbitrary asset import or production pagination. One unsaved working buffer can be replaced by starting another book; save drafts first. Dedication is shown in reader heading for manual books, while template dedication can be an actual prepended page; reconcile a canonical print model later.
- AI mock repeats/truncates six original passages, honoring name/language/count/target IDs only. It does not prove theme/age/density/educational quality. Advanced v2 interests/pronouns/requested-title/target metadata controls are not exposed.
- Opt-in recovery is per-tab session storage with bounded size, not encryption, synchronization or backup. It can be unavailable or fail. Orders and checkout details intentionally disappear on refresh. Browser reload does not restore in-flight generation.
- Only English/Hebrew reviewed; additional locales require translations/content/backend capabilities. USD is illustrative, not automatic local pricing. System font rendering varies across OSes.
- Chromium plus axe and scripted keyboard/swipe/reduced-motion checks are evidence, not exhaustive screen-reader, browser/hardware or WCAG certification. Reference-site research did not complete actual third-party purchases or guarantee their private widget behavior.

Stop after delivery for review. No push, merge, deployment or live provider/payment approval is implied.

## 11. Final verified delivery

- `npm test`: **108 passed**, 10 unit/component files.
- `npm run build`: strict TypeScript and Vite passed; approximately 366 kB JavaScript / 113 kB gzip, 58 kB CSS / 13 kB gzip. React remains the only UI runtime dependency.
- Full `npm run test:e2e` with installed Chromium: **24 passed** (12 scenarios across desktop/mobile), final run 1.9 minutes. Includes all three creation modes, template/character variation, physical book-language direction, keyboard and actual touch events, consent/reload/clearing, full English/Hebrew guest checkout, validation, declined simulation/retry, promo, history/details, reduced motion and 320/390/768/1024/1440px route sweeps.
- Axe A/AA tags (WCAG 2/2.1 and 2.2 on hardening/commerce routes): zero findings in final checked states. This is automated coverage, not a certification or exhaustive assistive-technology test.
- Tests that intercept network/API requests recorded no unexpected calls. No live provider/payment/backend integration was activated.
- Representative actual screenshots visually reviewed: storefront desktop, Hebrew checkout mobile and Hebrew reader desktop.
- Local-only commits and scope/whitespace checks complete. M5 implementation hash is recorded by the subsequent documentation commit below; use `git log --oneline` to retrieve the documentation commit itself.
