# StoryForge web

A React + TypeScript + Vite product demo with three independent creation journeys:

- **Create with AI**: a four-step reviewed brief, cancellable local sample generation, reading and explicit library save.
- **Personalize a Book**: original catalog, product previews and dynamic per-template personalization schemas. No AI calls.
- **Create Your Own**: page editor with text, ordering, layouts, backgrounds, original illustrations, preview, draft reopening and finalization.

All books and drafts live in React memory in the current tab. Refreshing or closing the tab loses them. There are no accounts, purchases, uploads or cloud saves. No backend server, keys or AI provider requests are required.

With Node 22.12+ and npm, from `frontend/`:

```sh
npm ci
npm run dev
npm test
npm run build
npm run preview
```

Open the local URL Vite prints (normally http://127.0.0.1:5173). Hash routes support browser history and direct links without a hosting rewrite. Start at `/#/` and use the three creation cards. `/#/books`, `/#/my-books`, `/#/create/ai`, `/#/studio/new`, `/#/help` are useful entry points. Synthetic sample books are preloaded into the demo library.

For browser checks after building:

```sh
npx playwright install chromium
npm run test:e2e
```

The Playwright runner owns a production preview on port 5186. It runs Chromium desktop and mobile projects, intercepts unexpected network/API requests, checks workflows, keyboard behavior, overflow and axe WCAG A/AA findings. An already installed compatible Chromium can be selected using `STORYFORGE_CHROMIUM_PATH` (absolute executable path). Screenshots are written to `../docs/frontend-screenshots/`; traces and transient reports are ignored. Only the Playwright browser installation requires a download; tests themselves use localhost and local assets.

Architecture: `src/pages/` holds product screens; `src/components/` holds shared covers/spreads/forms/reader; `src/domain/` holds the canonical frontend book model and exact brief normalization; `src/data/` holds typed versioned template fixtures; `src/routing/` implements hash routing; `src/hooks/` owns request cancellation and the memory library; `src/i18n/` contains typed locale dictionaries; `src/api/` retains the v2 HTTP seam and separate mock service. Original SVG artwork lives in `public/art/`.

The HTTP client is deliberately disconnected. Only an explicitly reviewed composition change should inject it into App; an unknown backend could call a paid provider. See [the complete handoff](../docs/FRONTEND_HANDOFF.md) for contracts, mock limits, screenshots and integration requirements.
