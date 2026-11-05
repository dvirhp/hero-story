# StoryForge web

Local React + TypeScript + Vite frontend. All visible generation uses an in-memory editorial sample. No API keys, backend, AI calls, accounts or storage are required.

From `frontend/`, with Node 22.12+ and npm:

```sh
npm ci
npm run dev
npm test
npm run build
npm run preview
```

Open the local URL printed by Vite. The default dev URL is http://127.0.0.1:5173. The preview command serves the built `dist/` directory. Do not publish this local foundation as a production service.

Start at `src/App.tsx`; reusable screens are in `src/components/`, brief normalization is in `src/domain/`, request lifecycle is in `src/hooks/`, and transport contracts/services are in `src/api/`. UI dictionaries and generation language descriptors live in `src/i18n/locales.ts`. No routing/state/i18n library is required yet.

The HTTP client is intentionally disconnected. It uses POST `/v2/stories/generate` only when explicitly constructed and injected. Connecting it can make paid provider requests depending on backend configuration. See [the full handoff](../docs/FRONTEND_HANDOFF.md) for contract sources, limitations and integration decisions.

Use the language selector to change interface direction; story language is independently selected in the form. Footer “Demo states” provides error and empty-reader previews. Form details remain in memory until the tab is refreshed or closed.
