# Frontend customer-journey QA matrix

Evidence date 2026-11-05. Tested delivered `1647d71`, reader `bd40358`, and latest committed expanded frontend `b09f54b`. Later uncommitted work is excluded.
The source is a local demonstration. “Verified” below means executed in that
environment; **none means FastAPI/PostgreSQL/payment integration**. “Confirmed issue”
means reproduced, “Not implemented” means absent from the captured UI, “Planned”
means acceptance specification only, and “Blocked” means a needed contract/service
or reviewer is unavailable. Priorities concern release/customer risk, not feature claims.

## Complete customer journey and creation modes

| ID / scenario | Level / priority | Status | Actual evidence / acceptance or dependency |
| --- | --- | --- | --- |
| J01 Home → catalog → product | Browser / P1 | Verified | Desktop/mobile, native links/history, filters/empty reset and product sample carousel; upstream + independent suites |
| J02 Product → child personalization | Browser / P1 | Verified | Product-specific controls render; unsupported companion/outfit controls absent on incompatible templates |
| J03 Personalization → preview → local saved reader | Browser / P1 | Verified with issues | Name/language/outfit/color update; ordinary dedication preview equals saved page; UX-03/05 remain |
| J04 Preview → format | Browser / P1 | Verified, local simulation | b09f54b softcover/hardcover/digital, quantity 1–10 and invalid 11 rejection; no real print/export |
| J05 Format → cart → quantity/remove | Browser / P1 | Verified, local simulation | Local snapshot/totals/empty recovery executed; UX-07 header accessibility fails |
| J06 Guest checkout → confirmation | Browser / P0 | Verified, local simulation only | Fictional details, discount, shipping choice, declined simulation/retry and confirmation/history; no real payment |
| J07 Account entry/sign-in/out | Browser/API / P0 | Not implemented | Clearly distinguish guest exploration from authenticated private storage; await approved session/auth contract |
| J08 AI creation four steps/review/cancel/sample/read/save | Browser / P1 | Verified, mock-only | Existing suites cover newborn en/he, explicit count and cancel; no real generation, educational quality or backend approval |
| J09 Template creation | Browser / P1 | Verified, local-only | Required fields, allowed choice, save and reopen; static original templates, no publication/inventory backend |
| J10 Manual creation/edit/reorder/remove/preview/finalize | Browser / P1 | Verified with issue | Stable IDs/order unit tests and actual browser text/order save/reopen; UX-04 warning loss remains |
| J11 Library filters/reopen/removal | Browser / P1 | Verified, memory-only | Original suites exercise filters/removal; independent saved template/manual reopen; reload permanence not promised |
| J12 Guest access without login | Browser / P1 | Verified, demo-only | Routes accessible; no secure anonymous ownership verified |
| J13 Unknown route/book, empty/search/error recovery | Browser / P2 | Verified | Upstream desktop/mobile tests; generation-error route is simulated, not an actual network failure |
| J14 Real frontend → FastAPI → DB save/read | Full local E2E / P0 | Blocked | Reviewed HTTP service composition, ownership and storage-aware APIs; do not substitute mock fetch or memory for this evidence |

## Detailed character and personalization matrix

Future acceptance cases are semantic specifications, **not invented server DTOs or
claims that every template should support every field**. Labels/options must come
from the approved template schema. Persist and render the same pinned values/version.

| Field / priority | Captured support / execution | Status | Required boundary, compatibility and preview tests |
| --- | --- | --- | --- |
| Child name / P1 | All templates; required focus, Hebrew/niqqud/mixed accented text browser check; 41-character unit rejection; literal marker/HTML-like name unit cases | Verified locally | Empty/whitespace, 1/40/41 Unicode code points, apostrophe/hyphen, emoji and long RTL/LTR wrapping; preserve exact text, no inferred gender; extend browser boundary cases |
| Gender/presentation / P1 | b09f54b Neutral/Boy/Girl state exists, but rendered SVG unchanged | Confirmed issue UX-08 / P3 | Define a documented effect or metadata-only wording; no inferred pronouns or prescribed stereotyped appearance |
| Skin tone / P1 | Deep selected; deterministic avatar and saved cover/page state checked | Verified locally, representative value | Full palette and incompatible-schema combinations remain planned |
| Hair color / P2 | Black selected; avatar state/source fill mapping inspected | Verified locally, representative value | Full palette contrast and combinations remain planned |
| Hairstyle / P2 | Long selected and saved; actual SVG shape branch inspected | Verified locally, representative value | Short/curls and all hat combinations remain planned |
| Eye color / P2 | Green selected; saved state/source fill mapping inspected | Verified locally, representative value | Exhaustive visual palette checks remain planned |
| Glasses / P2 | Checkbox on; rendered and saved avatar state checked | Verified locally, representative state | Repeated on/off, all hair/pose combinations remain planned |
| Freckles / P2 | Checkbox on; rendered and saved avatar state checked | Verified locally, representative state | All skin-tone visibility and toggling combinations remain planned |
| Clothing / P2 | Template raincoat/striped changes art/prose; avatar Sailor selected in b09f54b | Verified locally | Distinguish template outfit from avatar outfit; pairwise combinations remain planned |
| Accessories / P2 | Adventure hat activated by keyboard and retained on saved cover/page avatar | Verified locally, representative value | None/star-pin and all overlap combinations remain planned |
| Companion / P2 | sky-whale choice changes saved authored page; no affected page available in live preview | Confirmed issue UX-05 | Fox/rabbit updates exact affected text/art or explain text-only change; navigate preview to second page and check saved parity |
| Dedication / P1 | Optional textarea/prepended page; ordinary text works, placeholder-like text altered | Confirmed issue UX-03 | Preserve literal Unicode/markers/HTML text; 0/1/240/241 length, multiline, no silent substitution/truncation; optional max uses schema not global rule |
| Book language / P1 | en/he select; cover and BookSpread metadata change, book direction independent of UI | Verified locally | Both cross-language combinations, preserve names/values; block unsupported content language; no claim of other locales |
| Cover color / P2 | Offered for sky-whale/moon and compatible schemas; sky-whale selection verified; absent on small-hero | Verified locally with UX-06 risk | Every permitted color/art/title combination must meet actual text-background contrast; unknown choices rejected; no arbitrary CSS URLs |
| Template-specific schema / P1 | Separate companion/outfit/dedication/color field sets | Verified locally, incomplete product | Required/optional/default/unknown/incompatible controls, allowlisted choices; product changes clear incompatible values without leaking another book's data |
| Preview/saved version / P0 | Local template version demo-1 retained; preview first ordinary dedication matches saved reader | Partially verified | Backend immutable release/version pinning, asset/version changes, preview-save race and old Book unchanged after template updates remain blocked |

Pairwise appearance combinations and an exhaustive long-name/long-translation visual
set remain planned. The latest controls are actually rendered and exercised. Unused dictionaries alone remain insufficient evidence. The avatar is deterministic SVG, not generated illustration.

## High-priority physical book reader

| Scenario | Level / priority | Status | Evidence / next acceptance |
| --- | --- | --- | --- |
| Cover before prose; open and return to cover | Browser / P1 | Verified with UX-01 | Actual cover and book progression; Hebrew spine physically left despite right hinge |
| English desktop opening/physical spreads | Geometric browser / P1 | Verified | First page right beside blank left; later 2 left/3 right; exact sequence 1–6 |
| Hebrew desktop opening/physical spreads | Geometric browser / P1 | Verified | First page left beside blank right; later 2 right/3 left; exact sequence 1–6; binding remains UX-01 |
| Interface/book direction independence | Browser / P1 | Verified with UX-02 | Both opposite UI/book locale combinations retain physical order; reader tool translations can lag |
| Mobile single page / tablet breakpoint | Browser / P1 | Verified | One page below 900 px; actual requested 360/390/768 widths; no horizontal overflow |
| Next/previous, first/last disabled and numbering | Browser / P1 | Verified | Upstream and independent forward/backwards keys/bounds; no duplicate/skip in six-page sample |
| Touch page-turn direction | Chromium native touch emulation / P1 | Verified | CDP touch start/move/end advances he via right swipe and en via left swipe; not physical Safari/device testing |
| Keyboard arrows and thumbnails | Browser / P1 | Verified | Book-owned arrow mapping and page overview in upstream reader suite; interactive controls remain available |
| Fullscreen supported path | Browser / P2 | Verified | Actual fullscreenElement enter/exit in headless Chromium |
| Fullscreen denied/unavailable fallback | Browser fault injection / P2 | Planned | Assert safe localized notice and retained page; no false “fullscreen active” state |
| Text/art positioning and scaling | Browser/visual / P1 | Verified with UX-06 | Open spreads/art within horizontal bounds; closed cover title crosses dark illustration; long manuscript stress not exhaustive |
| Reduced motion | Browser media emulation / P1 | Verified | Cover transform none; spread animation none |
| Resize mid-book and orientation change | Browser / P2 | Planned | Current page remains in visible spread, no duplicate/skip, focus and progress preserved |
| Odd-ending/one-page books | Unit/browser / P1 | Partially verified | New physicalSpread unit includes odd/final leaf; existing one-page Hebrew AI browser path passes; independent long odd/even matrix remains planned |
| Long manuscript/long cover title | Browser/visual / P1 | Planned | Stress up to allowed bounds, logical order, no hidden/cropped words, usable scroll/zoom; no arbitrary fixed page clipping |

## Commerce matrix — executed local simulation and remaining specifications

b09f54b implements a local demonstration contract. Cases marked verified below were executed in the independent browser runner or unit suite. None proves real payment/order APIs, inventory, taxes, fulfillment or durable ownership.

| ID / scenario | Priority / status | Deterministic acceptance specification |
| --- | --- | --- |
| C01 Cart item | P1 / Verified local | Snapshot, format, quantity and simulated-only copy; unit source-mutation isolation; no provider calls |
| C02 Remove/undo | P1 / Partially verified | Remove and empty recovery passed; no undo implementation claimed |
| C03 Quantity | P1 / Verified local | Browser 1/2/10/11 and merge-over-max; unit zero/negative/fraction/NaN; no clamp |
| C04 Different personalizations/formats | P0 / Verified unit, browser extension planned | Separate configurations, identical snapshots merge, originals remain immutable; no full two-child browser flow yet |
| C05 Totals | P0 / Verified demo arithmetic | Browser hardcover 2=$78, 1=$39, discount=$3.90, standard total=$40.10, express confirmation=$47.10; unit integer-cent/digital shipping cases; tax explicitly not calculated |
| C06 Guest persistence | P0 / Blocked for durable guarantee | Current memory cart resets on reload, local/session storage empty; approved secure session/retention contract needed |
| C07 Checkout validation | P1 / Verified representative local cases | Empty contact errors/focus, fictional email/address advance; exhaustive Unicode/boundary validation planned |
| C08 Shipping | P1 / Partially verified | Fictional sample and express selection passed; source IL/US/GB choices use generic nonempty/length checks, not full regional postal validation |
| C09 Promo | P1 / Partially verified | STORY10 browser arithmetic and invalid REALCODE unit case pass; expiry/ineligibility/reapplication not implemented or verified |
| C10 Payment boundary | P0 / Verified simulation, real integration blocked | No card inputs, explicit no charge/no shipment; zero external/API requests, no real payment details |
| C11 Confirmation | P0 / Verified local simulation | Stable DEMO order summary and $47.10 express total; bag cleared; no paid/fulfilled claim |
| C12 Refresh/back/duplicate submit | P0 / Partially verified | Memory reset on reload verified; same-intent simulation idempotency unit case passes; real durable order idempotency blocked |
| C13 Failure/retry | P0 / Verified local simulation | Controlled decline retained cart; explicit retry succeeded; no bank/provider charge or error |
| C14 Order history/details | P1 / Verified local, secure scope blocked | Simulated order opens, Hebrew order details render; no private anonymous/account ownership |

Additional browser fixture concepts: two personalizations of one product plus a second product,
two allowed formats, quantities 1/2/max/max+1, Unicode names, a valid and expired
synthetic discount and explicit simulation failure. Monetary values/options follow the explicit demo policy or future approved server rules; these are not production API payloads.

## Accessibility, localization and data boundaries

| Scenario | Priority | Status | Actual evidence / missing check |
| --- | --- | --- | --- |
| axe WCAG A/AA including 2.2 tags | P1 | Confirmed issue UX-07 | Historical bd40358: 16 scans had zero violations. Latest b09f54b: 22/22 scans report header label-content-name-mismatch. No AA certification |
| Skip link, invalid-field focus, mobile menu Escape | P1 | Verified | Real keyboard and focus assertions |
| Missing accessible names / common forms | P1 | Verified, limited | No axe violations in tested states; not every future field/state |
| Cover contrast against art | P1 | Confirmed issue UX-06 | Visual/source-color ratio ~1.24:1; automated checker missed it |
| Touch-target size/spacing | P1 | Partially verified | Browser/axe common states; manual exception/spacing audit and dexterity review not complete |
| Screen reader, high contrast, zoom/reflow/focus obscured | P1 | Planned | Dedicated NVDA/VoiceOver/keyboard/400% review required; no WCAG 2.2 AA claim |
| All requested viewport widths | P1 | Verified, limited | Latest nine routes × five widths including empty cart/orders/format and opened reader; no horizontal overflow. Populated mobile checkout matrix not exhaustive |
| English/Hebrew navigation/forms/products/editor/errors | P1 | Verified, limited | Route/axe sweeps and actual creation flows; not native-language fluency review |
| Reader locale update | P2 | Confirmed issue UX-02 | Experience controls lag until unrelated rerender |
| Long translations/mixed numbers and strings | P1 | Partially verified | Mixed name and bilingual book/UI flows; exhaustive expansion/pluralization not executed |
| Dates/currencies/addresses | P1 | Partially verified | Library/order dates, English USD totals, fictional address and Hebrew order details rendered; timezone/rounding/address expansion not exhaustive |
| Future locales | P1 | Planned | Reviewed dictionaries/fonts/format/segmentation/direction rules and actual content/backend language support before exposing choices |
| No API/external calls in demo | P0 | Verified | Browser request guards and no attempted forbidden requests across passed suites |
| Private-book/session access security | P0 | Blocked | No authenticated/secure anonymous API composition; UUIDs and demo guest access are not access control |
| Refresh persistence and retention | P0 | Blocked for durable claim | Current local memory reset disclosed; future approved save/session/retention must be tested separately |

See [FRONTEND_UX_QA_REPORT.md](FRONTEND_UX_QA_REPORT.md) for severity, exact
reproduction, screenshots, commands and final result counts. A scenario specification
or a reproduced-defect probe is never a successful full integration test.
