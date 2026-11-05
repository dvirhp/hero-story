# StoryForge frontend, UX, accessibility and customer-journey QA

Independent Agent 4 review, 2026-11-05 (Asia/Jerusalem). QA worktree:
`C:\Users\dvir3\storyforge-qa`, branch `feature/storyforge-qa-foundation`.
No production component, backend, AI engine or other agent's worktree was changed.
No live AI, payment, purchase, merge, push or deployment was performed.

## Outcome and source boundary

Final frontend evidence is pinned to b09f54b. The b09f54b test run and its
accessibility failures supersede any earlier all-green summary; earlier revision
results remain historical comparisons, not current release approval.

The current captured frontend supports real **local-demo interactions** for discovery,
AI sample creation, template personalization, manual editing, memory-only save/reopen,
and reading. The expanded b09f54b revision also provides a complete **simulated**
format/cart/guest-checkout/confirmation journey, with no real purchase or backend
integration. Demo banners correctly disclose that boundary; missing server integration
is not reported as a frontend defect.

Eight UI findings were reproduced: two P1, four P2 and two P3. No P0 was established.
The physical reader's tested page ordering, direction-aware keys/touch, desktop spreads,
mobile pages, reduced motion and fullscreen work. Its Hebrew cover spine and cover
title contrast still need correction. Zero axe violations does not mean WCAG conformance.

Three independently built source revisions were exercised:

| Revision | Meaning | Actual checks |
| --- | --- | --- |
| `1647d71d7fa83ceec9aace4c72d5b822adc435f5` | Delivered three-mode product frontend before physical-reader redesign | 74 unit/component tests, production build and 12 Chromium browser tests passed |
| `bd40358aa88c090d012dc0a47c067d5b3bd616de` | Latest committed physical-reader implementation at capture | 75 unit/component tests, production build and 14 Chromium browser tests passed; independent QA checks below |
| `b09f54bc3ba0f6b175b71a80b7a3965b8d23429d` | Expanded character, gallery and simulated commerce revision; final review target | 87 unit/component tests and build passed; upstream browser accessibility failures and independent results below |

Initial inspection found reader changes in progress; they were committed before the
first source capture. All 52 captured frontend files were checked against bd40358
after Git CRLF normalization. Their exact captured-byte hashes are in
[source-manifest.json](qa-screenshots/frontend-ux/source-manifest.json). Agent 2 then
continued implementation, then committed b09f54b. That committed revision was exported
to `qa/.local/frontend-ux-latest` using `qa/export_frontend_revision.py`, without
copying its later uncommitted recovery/session changes. The latest manifest/results
are under `docs/qa-screenshots/frontend-ux-latest/`. Findings below were remeasured
against b09f54b; UX-01 through UX-06 remain present. Later uncommitted work is excluded
and must be revalidated after delivery before closing findings.

Read the source, frontend tests, routing, catalog/schema fixtures, memory-library
implementation, FRONTEND_HANDOFF.md and the premium audit. Inspected prior actual
desktop reader/mobile personalization screenshots, then captured and inspected new
QA screenshots. The handoff's older 74/12 counts and “swiping is not implemented”
statement describe 1647d71; bd40358 has 75/14 and implemented touch gestures.
The older handoff is now incomplete: b09f54b actually renders character controls,
gallery/sort and commerce, which were absent in bd40358. Those newer capabilities
were tested from source rather than inferred from translation strings or the handoff.

## Inventory: actual behavior versus proposed product

| Area / actual routes | Classification | Verified behavior / boundary |
| --- | --- | --- |
| Home `#/`, catalog `#/books`, product `#/books/:id` | Working local frontend | Six static books, filters, sorting/gallery source, empty/reset recovery, product descriptions and samples; no inventory service; original navigation tests fail the new header axe check |
| Personalization `#/personalize/:id` | Working local, partial preview | Per-template required fields, allowed choices, name, companion/outfit where supported, dedication, cover color where supported and en/he; memory save/read; UX-03/05 apply |
| AI wizard `#/create/ai` → `#/generating` → reader | Mock-only generation | Validated/reviewed brief, explicit pages, cancellation, sample prose and explicit local save. No FastAPI calls; sample does not fulfill semantic guidance/age/learning promises and says so |
| Manual `#/studio/new`, `#/studio/:id` | Working local editor | Add/edit/delete/reorder, stable page IDs, layout/color/art selection, explicit draft save/reopen, preview and finalization validation. No autosave/cloud persistence; UX-04 applies |
| Library `#/my-books` | Working memory-only frontend | Three seed samples/drafts, status filters, reopen/edit and confirmed removal; refreshed memory is reset. No account ownership or server persistence |
| Reader `#/read/:id`, `#/read/sample-:id-:language` | Working local with defects | Cover/open, desktop physical spread, mobile single page, keys/native touch emulation, thumbnails, fullscreen and reduced motion; UX-01/02/06 apply |
| About/help/privacy and missing/error routes | Working local frontend | Recoverable missing-route/book views and accessible disclosures; error demonstration is not actual server failure recovery |
| Guest experience | Working unauthenticated demo only | Browse/create/read and simulated checkout without login; memory-only cart; no secure anonymous session/private API verification |
| Account entry/sign-in | Missing | No mounted account flow; not a broken authentication implementation |
| Format → cart → checkout → order | Working local simulation | Mounted `#/format/:id`, `#/cart`, `#/checkout`, `#/confirmation/:id`, `#/orders`, `#/orders/:id`; quantities, discount, fictional shipping, simulated decline/retry and order snapshot; no payment collection or shipment |
| Character appearance | Working deterministic local avatar with UX-08 | Schema-controlled presentation, skin/hair/eye, glasses/freckles, outfit/accessory controls; saved cover/page avatar; no generated illustration; presentation metadata has no visible effect |

The full expected conversion flow can now be executed **as a local simulation**:
Homepage → Catalog → Product Detail → Personalize → Preview/Save/Reader → Format →
Cart → Guest Checkout → Simulated Confirmation. The upstream new commerce tests and
independent runner exercise it; not every device/state combination is covered.
Only fictional names, `demo@example.test` and sample address values were entered.
There are no card inputs or real payment requests, and the UI says no payment or
shipment occurs. Account entry, durable guest persistence and backend integration
remain missing rather than failed implemented services.

## Prioritized confirmed findings

Severity: P0 security/data-loss emergency; P1 blocks the affected critical requirement
or accessibility target; P2 functional/local-state correctness; P3 limited feedback or
polish. Missing unimplemented features are listed separately rather than inflated into
confirmed defects. The initial six have historical characterization probes in
`qa/e2e/frontend-ux-review.mjs`; the new `frontend-regression.mjs` remeasures them
and records present/resolved/unverified states instead of asserting that defects
must remain. Neither type of probe is counted as a desired-UX product pass.

| ID | Priority | Finding | Scope/history |
| --- | --- | --- | --- |
| UX-01 | P1 | Hebrew physical cover still draws its spine on the left | Existing cover styling omission conflicts with the critical right-bound Hebrew book requirement; page spread order itself passes |
| UX-06 | P1 | Cover title crosses dark artwork with approximately 1.24:1 contrast | Confirmed visual/accessibility issue; readable external page heading does not repair the cover preview |
| UX-02 | P2 | Reader tool labels lag behind an interface-language change | Regression introduced by reader redesign's new experience labels; not a book-direction regression |
| UX-03 | P2 | Dedication text is interpreted as template placeholders | Existing local data-substitution defect; no script execution was demonstrated |
| UX-04 | P2 | Preview → continue editing clears unsaved reload warning | Existing editor lifecycle defect; unsaved content remains visible but warning state is lost |
| UX-05 | P3 | Companion change has no inspectable live-preview feedback | Existing partial preview functionality; saved story does contain selected companion |
| UX-07 | P2 | Header cart accessible name does not contain visible label/count | Confirmed new axe `label-content-name-mismatch` regression in expanded commerce revision |
| UX-08 | P3 | Presentation choice changes stored state but not rendered character | New avatar preview feedback gap; no stereotyped gender design is prescribed by QA |

### UX-01: Hebrew cover binding contradicts book direction

Reproduce: open `/#/read/sample-moon-fox-he` at 1440 px. Before opening, inspect the
cover. The physical container declares RTL and right hinge, but `.book-spine` is
visibly on the **left**; its bounding box is on the left half of the cover. Repeat
with English UI or Hebrew UI: binding must follow the book, not interface locale.
Expected: Hebrew spine/hinge/page-edge styling consistently on the right.

[Screenshot](qa-screenshots/frontend-ux/UX-01-hebrew-cover-left-spine.png).
Cause: `components/BookCover.tsx` emits the spine; `styles.css:471` fixes it with
`left: 0` and a right border, while reader rotation uses the right transform origin.
Recommendation: derive binding, corner rounding, page-edge shadow and spine gradient
from book direction; retain passed geometric page-position tests and add the cover's
actual bounds rather than relying only on `data-hinge` attributes.

### UX-06: cover title loses contrast over illustration

Reproduce: open `/#/read/sample-moon-fox-en`, leave cover closed at 1440 px.
The second title line extends into the purple illustration area. Computed text is
`#253c42`, 36 px bold, while `moon.svg` paints the underlying top illustration region
`#414271`. Their source-color contrast is **1.2433:1**; title/image bounding boxes
overlap by about 67.9 px. Screenshot confirms visibly dark-on-dark title text.

[Screenshot](qa-screenshots/frontend-ux/UX-06-cover-title-contrast.png).
This misses even the 3:1 large-text threshold in
[W3C's SC 1.4.3 explanation](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
It is dynamic DOM title text intended for reading, not an incidental label inside
a photograph. Ratio uses authored colors rather than antialiased screenshot pixels;
SVG texture does not make the roughly 1.24 ratio adequate.

Cause: BookCover chooses `--cover-ink` from the plain `coverColor` alone; the art covers
81% of the cover and can sit behind multiple title lines. Recommendation: reserve a
solid, contrast-safe title region or use a verified plate/background across all title
lines. Test long English/Hebrew names, wrap and every art/color combination. Axe's
zero-result scan did not establish the actual image-background contrast.

### UX-02: interface locale change leaves English reader tools

Reproduce: open `/#/read/sample-moon-fox-en`; change Interface language to Hebrew.
HTML and normal navigation change to RTL/Hebrew, but “Page overview”, “Read fullscreen”,
spread-mode label and hint remain English. The Hebrew “מפת עמודים” button is absent.
An additional reader interaction can incidentally trigger a corrective rerender.
Expected: all interface labels change together; book language stays English.

[Screenshot](qa-screenshots/frontend-ux/UX-02-hebrew-ui-english-reader-tools.png).
Cause: `StoryReader.tsx:10` reads `document.documentElement.lang` during render before
App's locale effect updates it. Recommendation: pass a reactive locale prop/context
to the reader; use book.language only for physical direction. Add both UI/book
language cross-combinations and immediate locale-switch assertions.

### UX-03: dedication is changed without permission

Reproduce: personalize sky-whale; name `Maya`; dedication
`Dear {{name}}, from {{companion}}.`. Click Peek inside, save, then open the book.
Actual preview and saved first page: `Dear Maya, from fox.`. Expected: preserve
the adult's literal dedication exactly; placeholders belong to authored template
content unless an explicit dedication-template feature is approved.

[Screenshot](qa-screenshots/frontend-ux/UX-03-literal-dedication-changed.png).
Cause: `data/catalog.ts:385` prepends raw dedication to the authored page list, then
`:412` applies `replace(line)` to every page. Existing unit coverage preserves
markers in a supplied name but misses this dedication path. Recommendation: apply
substitution only to authored template text; append/dedicate literal user content
afterward. Add markers, Hebrew, emoji and HTML-looking text to literal-field cases.

### UX-04: unsaved warning disappears after preview

Reproduce: create a manual book, edit title and page text without saving. At this
point a cancelable beforeunload event is prevented. Choose Preview book, then
Continue editing. The unsaved text is still there and the UI says changes are not
saved, but the same event is **not prevented**. Expected: preview should not mark
unsaved work clean or remove its reload/close guard.

[Screenshot](qa-screenshots/frontend-ux/UX-04-unsaved-preview-roundtrip.png).
Cause: `Studio.tsx:38` initializes local notice/dirty state to clean on remount;
preview unmounts the editor. Recommendation: keep saved-versus-working revision/dirty
state in the draft owner, independent of ephemeral notice text, and preserve it through
preview. Browser evidence checks event prevention; an actual forced-reload loss was
not required or claimed. Memory reset on ordinary refresh is a disclosed demo limit.

### UX-05: selected companion cannot be checked in live preview

Reproduce: personalize sky-whale, enter a name, choose Peek inside, change Fox to
Rabbit. Actual preview is unchanged and provides no page-selection control. The
companion occurs on the second authored page; `Personalize.tsx:170` renders only
`book.pages[0]`. Adding a dedication makes the only preview page the dedication.
Expected: a way to inspect the affected page or an accurate explanation of which
page changes. Saved story substitution itself works.

[Screenshot](qa-screenshots/frontend-ux/UX-05-companion-preview-no-feedback.png).
Recommendation: add bounded full-book preview navigation or focus the affected page;
test each schema control against its actual target text/art and maintain parity with
the saved snapshot. No backend change is needed for this local feedback gap.

### UX-07: cart accessible name does not match visible label

Reproduce on b09f54b: load the home page with an empty bag. The header cart link
has aria-label `Your bag (0)` and visible content `Your bag 0` plus its icon. Axe
reports `label-content-name-mismatch`, serious impact, on `.bag-link`. The same
failure appears in all 22 independently scanned route/locale combinations. The
original product browser tests fail their accessibility assertions because of it.

[Latest screenshot](qa-screenshots/frontend-ux-latest/UX-07-cart-accessible-name.png).
Expected: the accessible name contains the rendered visible label in a compatible
sequence, with any count description handled consistently. Recommendation: prefer
the native text-derived link name, hide the decorative icon from assistive technology,
and expose the count without rewriting the label inconsistently. Retest both locales,
zero/nonzero quantities, narrow layout and speech/keyboard activation. Do not simply
disable the axe rule or remove accessibility assertions.

### UX-08: character presentation selection has no visible effect

Reproduce on b09f54b: open sky-whale personalization and change Neutral to Girl.
The selected button/state changes, and data-character stores `presentation: girl`,
but the rendered avatar SVG is identical after removing only that metadata attribute.
Source CharacterPreview never consumes presentation. Other appearance controls do
affect the avatar and persist into the saved cover/page snapshot.

[Latest screenshot](qa-screenshots/frontend-ux-latest/UX-08-presentation-no-visible-effect.png).
Recommendation: define the intended product meaning; implement its documented effect
or identify it as metadata-only instead of implying every choice updates the preview.
QA does not prescribe stereotyped visual gender differences or infer pronouns from
appearance. This is a P3 feedback/contract gap, not failed avatar persistence.

## Reader, responsiveness and accessibility evidence

Independent checks used actual **geometry**, not just direction attributes:

- English first page opens on the right; Hebrew first page opens on the left beside
  the right inside-cover leaf. Later English 2/3 spreads place 2 left, 3 right;
  Hebrew places 2 right, 3 left. Sequence observed exactly 1–6, no skipped/duplicate
  pages; backward keys return to 4/5 after the final page.
- Book-owned spread order was also exercised with the opposite interface locale.
  Direction-aware native touch-event emulation via Chromium CDP advances single
  mobile pages in both languages. This is not evidence from physical devices/Safari.
- Fullscreen entry/exit succeeded in headless Chromium. Reduced-motion context
  produced no spread animation and no cover transform.
- 360/390/768/1024/1440 px: seven representative routes each in bd40358 and nine
  routes including cart/orders/format in b09f54b, plus opened reader,
  had no document horizontal overflow; spread bounds remained inside the viewport.
  Desktop spreads apply from 900 px; mobile/tablet below that use single pages.
- Keyboard skip-link activation, invalid-field focus and mobile-menu Escape/focus
  return passed. No keyboard trap was observed in these exercised paths.
- Initial bd40358: sixteen axe scans (eight routes × English/Hebrew) reported zero
  automated violations. Latest b09f54b: **22/22 scans report UX-07**. These use WCAG
  2 A/AA, 2.1 A/AA and 2.2 AA tags. UX-06's cover contrast remains a separate visual
  issue. Neither the earlier zero result nor current functional passes certify AA.

Reader screenshots: [English desktop](qa-screenshots/frontend-ux/reader-en-desktop.png),
[Hebrew desktop](qa-screenshots/frontend-ux/reader-he-desktop.png),
[English mobile](qa-screenshots/frontend-ux/reader-en-mobile.png),
[Hebrew mobile](qa-screenshots/frontend-ux/reader-he-mobile.png).
Screen-reader output, forced colors, browser zoom/reflow at 400%, all focus-obscuration
cases, and full target-spacing exceptions remain manual/extended checks. Some text
and controls are small; do not declare a target-size failure from height alone because
[SC 2.5.8 includes spacing/equivalent/inline exceptions](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).

## Localization and persistence boundaries

Verified English/Hebrew route sweeps, names with niqqud and accented/mixed-script
text, book-versus-interface direction independence and Hebrew editor text metadata.
UX-02 is the localized reader failure. Native linguistic quality and exhaustive
long-translation expansion were not reviewed. The original English brand imprint
is artwork/branding, not evidence that a third generation language is supported.
Only en/he is exposed as a functional locale/generation choice in this snapshot.

Library dates use Intl.DateTimeFormat with Asia/Jerusalem; their actual display
appears in exercised library screens, but timezone-boundary fixtures were not run.
Latest b09f54b mounts commerce: English USD totals, fictional contact/address values,
confirmation date and Hebrew order-details UI were exercised. The source exposes
IL/US/GB country choices but uses generic nonempty/length checks, not complete regional
postal validation. Currency/address/date boundary cases are not exhaustively verified.
Future locales need
reviewed dictionaries, plural/date/number/currency/address formats, fonts/segmentation,
page-direction strategy, long-string tests and actual backend capability support.

Saved books/drafts are cloned React snapshots only. Explicit save/reopen within the
running app works; refresh/reset persistence, auth/session ownership, cross-user access,
concurrent revisions and server failures remain backend-dependent. No claim of cloud
or durable guest-session saving is made by this report or exercised demo.

## Automation, results and reproduction

Environment: Windows; Node 22.16.0/npm 10.9.2; Playwright Test 1.64.1;
axe-core Playwright wrapper 4.14.0; cached Chromium build 1228. Dependencies were
copied to QA-only directories; `npm ls --depth=0` passed. No package/browser download.
Independent browser runners blocked external/API requests before transport and
recorded zero attempts and browser exceptions in their final runs. Upstream suites
have their own guards; no uniform upstream request-monitoring coverage is claimed.

| Run | Actual result | Limitation |
| --- | --- | --- |
| Delivered 1647d71 Vitest/build | 74 passed, 0 failed/skipped; build passed | jsdom/mock HTTP, not backend integration |
| Delivered 1647d71 upstream Playwright | 12 passed, 0 failed/skipped, about 1.0 min | Real desktop/mobile Chromium over demo services |
| Current bd40358 Vitest/build | 75 passed, 0 failed/skipped; build passed | Separate captured source; no server integration |
| Current bd40358 upstream Playwright | 14 passed, 0 failed/skipped, about 1.1 min | Includes new reader tests |
| Historical bd40358 independent UX runner | 17 functional checks passed; 6 issues reproduced; 0 unexpected harness failures/skips | 23 scenario groups, including 16 axe scans; reproduced issues are not product passes |
| Latest b09f54b Vitest/build | 87 passed, 0 failed/skipped, build passed | 7 test files; 16.10 seconds; still jsdom/local simulation |
| Latest b09f54b upstream Playwright full run | 5 passed, 13 failed, 0 skipped, about 1.5 min | Twelve failures report UX-07; one mobile reader connection failure was transient |
| Latest isolated mobile reader rerun | 1 passed, 0 failed/skipped, 4.8 seconds | Reproduces the previously transient path successfully; does not erase the initial failed run |
| Latest independent browser regression | 17 functional checks passed; 8 finding probes inspected; 1 axe sweep inspected; 0 harness failures/unverified cases | 26 scenario groups; all 8 findings present, 22 axe scenarios affected by UX-07 |

[Machine-readable independent results](qa-screenshots/frontend-ux/results.json).
Latest results: [b09f54b results](qa-screenshots/frontend-ux-latest/results.json).
The latest axe sweep is recorded as inspected, not passed: detected violations are
reported under UX-07. An attempted further full upstream rerun was blocked before
any tests because port 5186 was already occupied; that process was left untouched.
The independent latest runner used a newly owned preview on port 4197 instead.
There is no numerical source/branch coverage claim and no backend/full-stack E2E
execution in this assignment. Earlier harness runs needed selector corrections and
async fullscreen synchronization; those setup mistakes were corrected and rerun, not
reported as product defects. No product fix was applied to obtain the final results.

From QA root, prepare snapshots once using `python qa/capture_frontend_review.py`.
It refuses to overwrite existing snapshots. Source snapshots/dependencies/builds are
ignored under `qa/.local/`; screenshots and sanitized results are tracked here.

```powershell
Push-Location qa/.local/frontend-ux-current/frontend
npm test
npm run build
$env:STORYFORGE_CHROMIUM_PATH = 'C:/Users/dvir3/AppData/Local/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-win64/chrome-headless-shell.exe'
node node_modules/@playwright/test/cli.js test --reporter=line
# Start this owned preview server in a separate terminal:
node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4194 --strictPort
```

From a QA-root terminal while that server runs: `node qa/e2e/frontend-ux-review.mjs`.
For the older baseline, repeat npm/build/upstream Playwright in
`qa/.local/frontend-ux-base/frontend` after the current upstream run finishes;
both upstream configs own port 5186 and must run sequentially. Tool paths are local
and may be overridden via the runner's environment variables. Stop owned servers.

The historical independent runner's UX-* probes intentionally assert the **observed defect**
on the pinned revision and report `defect reproduced`. They are diagnosis evidence,
not desired-behavior release tests. Replace with corrected expectations when validating
Agent 2's fix; a characterization test passing never closes the issue.

For the latest pinned revision, use the following command only if that directory
does not already exist; it refuses overwrite:

```powershell
python qa/export_frontend_revision.py b09f54b frontend-ux-latest
```
Run npm tests/build/upstream browser tests in its frontend directory. Start a separate
QA-owned preview with the direct Vite command on port 4197. From QA root:

```powershell
$env:STORYFORGE_UX_URL = 'http://127.0.0.1:4197'
node qa/e2e/frontend-regression.mjs
```

This newer runner reports present/resolved/unverified for each finding rather than
requiring old defects to remain. Both exporters write only ignored QA snapshots.
Later source working changes are not implicitly imported. All 65 latest snapshot
files were verified byte-for-byte against the committed archive.

## Missing features, release criteria and Agent 2 handoff

The full character palette and simulated commerce now exist locally; richer preview,
clear presentation semantics, secure account/session ownership and durable library/
draft/cart/order storage remain product work. Detailed cases, dependencies and acceptance
criteria are in [FRONTEND_E2E_TEST_MATRIX.md](FRONTEND_E2E_TEST_MATRIX.md). The latest
same-product variant separation, snapshot immutability, digital shipping=0, invalid
quantities and simulation idempotency also have passing unit cases; this is not a
real payment or server idempotency guarantee.

Before claiming a complete journey: render supported schema fields only; preserve user
text; provide reliable edit/preview/save state; complete local deterministic format/cart/
checkout/confirmation with honest simulated pricing/payment copy; then independently
validate real local APIs/session ownership/persistence after approved composition.
No real payment information, paid-provider access or production testing is authorized.

QA implementation/evidence commits: `434cc8eb940229adb4caa963a1efbaa7e4eeef16`
(reader baseline) and `aaeec8fa1bde6aba354a92cc81cc7e426c54dcf5` (expanded regression).
The documentation commit is discoverable with
`git log -1 --format=%H -- docs/FRONTEND_UX_QA_REPORT.md`.

[Concise Agent 2 handoff](FRONTEND_AGENT2_QA_HANDOFF.md) lists fix priorities and
revalidation. Do not merge this QA branch or alter another agent's worktree as part of
this report. Reproduce and fix in the owning frontend branch, then request independent
verification of the completed revision.
