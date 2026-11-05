# StoryForge web

A React + TypeScript + Vite customer-experience demonstration with three distinct creation journeys and a shared book reader:

- **Create with AI**: reviewed brief, exact age normalization, explicit page count, optional local avatar, cancellable sample generation, saving and independent editable copies.
- **Personalize a Book**: local versioned catalog, discovery/gallery, dynamic template fields and character schemas, live cover/text preview and saved personalized books.
- **Create Your Own**: interactive text/layout/art editor, page duplication/order/removal, illustration positioning, cover/dedication, preview, draft reopening and finalization.
- **Demo shopping**: format/quantity, configuration-aware bag, guest checkout, illustrative shipping/promo, no-card payment simulation, confirmation/history/details. No real stock, purchases, charges, printing or shipping.

Default state stays in React memory. The footer offers optional **sessionStorage recovery** for books, drafts, AI brief, UI locale and bag after refresh. It requires consent and can be cleared there; closing the tab clears the session. Checkout contact details, addresses, emails, orders, job keys and tokens are never persisted. This is not a backup. Use fictional details in checkout.

No backend server, keys, external fonts or AI provider requests are required. All offers/catalog/generation are visibly mocked; the typed v2 client and proposed v3 ports are disconnected. No configuration flag silently enables live generation.

With Node 22.12+ and npm, from `frontend/`:

```sh
npm ci
npm run dev
npm test
npm run build
npm run preview
```

Open the URL Vite prints (normally http://127.0.0.1:5173). Hash routes support history/direct links without hosting rewrites. Useful entries: `/#/`, `/#/books`, `/#/create/ai`, `/#/studio/new`, `/#/my-books`, `/#/cart`, `/#/orders`, `/#/help`.

Browser checks after building:

```sh
npx playwright install chromium
npm run test:e2e
```

Playwright owns a production preview on port 5186 and tests Chromium desktop/mobile, en/he, physical RTL/LTR reading, keyboard/touch, consent recovery, all three creation modes, guest checkout/failure recovery, cross-width overflow and axe checks. Set `STORYFORGE_CHROMIUM_PATH` to an existing compatible Chromium executable when necessary. Screenshots go to `../docs/frontend-screenshots/`; reports/traces/build/dependencies are ignored. Browser installation downloads once; tests use localhost/local assets.

Architecture: `pages/` screens, `components/` shared UI/reader/form, `personalization/` typed schema/character renderer, `domain/` pure book/brief logic, `data/` original catalog fixtures, `commerce/` pure bag/quote models and mock checkout, `state/` opt-in recovery, `hooks/` cancellation/library, `routing/` native hash navigation, `i18n/` reviewed locale registry/dictionaries/fallback, `api/` v2 client and proposed future product ports. React and ReactDOM are the only runtime dependencies.

See [the handoff](../docs/FRONTEND_HANDOFF.md) for exact contracts, milestones, screenshots, checks and remaining integration work, and [the audit](../docs/reviews/FRONTEND_PREMIUM_AUDIT.md) for reference research and gap analysis. Any real integration must preserve backend-owned ownership, quotas, quotes and AI acceptance rather than reusing demonstration policies as authority.
