# Premium customer experience audit and implementation plan

2026-11-05. Baseline `1647d71`; isolated frontend branch. This is an audit of working behavior, not a screen-count claim.

| Classification at baseline | Evidence / gaps |
| --- | --- |
| Functional local interactions | Catalog search/category/age/language, per-template forms, literal name/dedication substitution, manual add/remove/reorder/text/layout/color, cover and page navigation, memory save/reopen, validation and cancellation. 74 unit/component and 12 Chromium cases previously passed. |
| Mock only | AI text and approval; catalog inventory; library ownership and persistence; artwork is original static illustration, not generated or a full avatar. |
| Partial | Reader has language-aware keys but only one page, no physical spreads/opening/touch/fullscreen. Appearance only switches one outfit asset. Discovery has no sort/gallery. Localization has typed dictionaries but some component literals. Manual editor lacks duplicate/position/cover/dedication controls. |
| Missing | Cart, quantities/configuration identities, format selection, shipping/contact/payment boundary, promo flow, confirmation/history/details; session recovery, authoritative quota/async job adapter. |
| Backend dependent | Real catalog/template schemas, owned books, revisions, session/CSRF, async execution, quotas, server quotes/stock/tax/shipping, payment verification and fulfillment. Agent 3 v3 contracts are proposals, not executable endpoints. |

Baseline UX gaps: there is no conversion path after preview; narrow pages require too much scrolling; editorial covers dominate interactive feedback; separate illustration/text panels look like a slideshow. The interface changes direction, but physical Hebrew cover/spread order is absent. Prior automated checks do not establish WCAG 2.2 AA or production readiness.

## Reference comparison (primary pages inspected read-only)

| Experience | Wonderbly | Hooray Heroes | Librio | StoryForge action |
| --- | --- | --- | --- | --- |
| Discovery | Age/theme/occasion navigation and product shelves | Recipient/child-count collections and search | Product filters and language-led discovery | Add sorting, gallery, format information and clearer next action. |
| Personalization | Character/name/dedication and full-book preview emphasized | Creation guide explains appearance and book-specific choices | Product journey supports illustrated personalized characters and language options | Build schema-controlled deterministic avatar, with no assertion of AI illustration support. |
| Product reassurance | Preview, format/quality and fulfillment details near CTA | Binding/page/size information, cart and support | Product previews, language choices and material/value information | Show demo-only formats/prices and transparent mock limits; do not invent reviews or shipping promises. |
| Commerce | Cart and ordering entry points | Cart, checkout, localized country/currency and tracking | Cart/commerce/localized product navigation | Complete guest demo cart→checkout→simulation/history with typed services; no live purchase. |
| Reader / mobile | Product imagery and preview-before-buy journey | Product/creation guidance; interactive preview is client-rendered | Illustrated previews and customization entry | Independently implement physical RTL/LTR spreads, touch, keyboard, reduced motion and mobile single pages. |

Sources: [Wonderbly product](https://www.wonderbly.com/personalized-products/i-spy-you-search-and-find-book), [Wonderbly home](https://www.wonderbly.com/), [Hooray Heroes product](https://hoorayheroes.com/products/hooray-you-did-it), [creation guide](https://hoorayheroes.com/blogs/stories/book-creation-process), [Librio catalog](https://librio.com/en/personalized-childrens-books), [Librio product](https://librio.com/en/personalised-childrens-books/the-sneezing-dragon). Some customizers/checkout details are client-rendered or unavailable without a product interaction; no live purchase, account, PII submission, payment or guaranteed behavior was tested on these sites. Matrix distinguishes visible features from our implementation recommendations. No third-party content/assets are copied.

## Prioritized milestones

1. Design tokens/navigation and physical reader: deep ocean/turquoise/peach identity, correct book-owned opening, desktop paired pages, mobile single pages, touch/keyboard/fullscreen/thumbnails. Independently test direction/order, build, Chromium screenshots; commit runnable result.
2. Catalog and per-template character configuration: sorting/gallery, original deterministic avatar, schema-supported controls/validation, live preview and varied capability fixtures. Verify unit/component/browser behavior; commit.
3. Commerce frontend: fixture offers, configuration-keyed cart, quantities, guest checkout/validation, explicit demo shipping/discounts/payment simulation, failure/confirmation/history/detail. Authoritative business and provider seams remain typed and mocked; test totals, duplicate/config separation, no-card collection and both languages; commit.
4. Creation refinements: AI appearance kept outside StoryRequestV2; separate proposed async/session/usage ports; manual duplication, placement, cover/dedication, edited-source provenance, eligible demo cart entry and opt-in tab recovery. No invented v3 network requests. Test boundaries; commit.
5. Hardening: dictionary fallback/locale formatting, translated complete journeys, WCAG 2.2-oriented automated and keyboard checks, wide/narrow/RTL sweeps, production build and actual screenshots. Update handoff with verified limits and commits.

Acceptance: Homepage→Catalog→Product→Personalize→Book preview→Demo format→Cart→Guest checkout→Simulated order confirmation, plus complete AI/mock and manual creation. No live providers, cards, shipping, purchases, login wall, backend changes or deployment.

## Milestone 1 — verified reader and visual foundation

Implemented ocean/turquoise/pearl design tokens and physical book-owned direction. Hebrew opens from the right and places pages 2/3 on right/left; English is mirrored. Narrow screens use one page; touch/keys/buttons, thumbnails, fullscreen request/failure and reduced motion are available. Source remains local demo; no live integration. Unit/component suite: 75 passed; focused Chromium reader cases: 2 passed, both languages in desktop/mobile, with actual swipe events and physical-side assertions. Strict production build passed. Screenshots: `reader-premium-{en,he}-{desktop,mobile}.png`. Commerce, richer character controls and async/backend services remain for subsequent milestones.
