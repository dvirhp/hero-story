# Browser verification and deferred integration

## Executed snapshot checks (2026-11-05)

The QA baseline has no frontend, but Agent 2's committed React frontend is now
available in a separate branch. `browser-regression.mjs` was executed against an
isolated export of commit c2b72c2: eight scenarios passed in real Chromium using
the app's mock service. No API/database integration or template/editor coverage
is claimed. The snapshot and copied dependencies live under ignored `qa/.local/`.
The QA strategy/matrix list exact scope and blocked workflows.

From the QA root, these local commands reproduce the setup using already installed
tooling, without editing another worktree or downloading packages:

```powershell
python qa/prepare_snapshot.py frontend
Push-Location qa/.local/frontend-snapshot/frontend
npm test
npm run build
node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4184 --strictPort
# Server runs in foreground; in a second QA-root terminal:
$env:STORYFORGE_PLAYWRIGHT_MODULE = 'C:/Users/dvir3/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright/index.mjs'
$env:STORYFORGE_CHROMIUM = 'C:/Users/dvir3/AppData/Local/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-win64/chrome-headless-shell.exe'
node qa/e2e/browser-regression.mjs
```

Stop only the server you started when finished. Snapshot preparation refuses to
overwrite an existing snapshot. The hardcoded local module/browser locations are
environment-specific; set the two environment variables to your own installed
Playwright module and browser when reproducing elsewhere. Verified Playwright
version: 1.62.0; Chromium cache build: 1228. No installation was performed by QA.
This executable runner uses Playwright's browser API and node assertions, not the
optional Playwright Test spec/config below. The spec/config remain unexecuted.

## Optional future Playwright Test configuration

No frontend or package.json exists on baseline 5ae24e9. These optional files are
an unexecuted smoke foundation, not story journey coverage. They do not start a
server, install packages, change shared config, or connect to paid providers.

After integrating Agent 2's reviewed frontend, install a pinned @playwright/test
and its Chromium browser in an isolated tooling environment (installation may
need network). Run its executable with `test --config qa/e2e/playwright.config.ts`.
Set STORYFORGE_E2E_URL to a local frontend explicitly wired to a fake-only API.
The smoke check blocks external page requests and disables content artifacts.
Do not use real child data. Review and lock tooling versions when integration
becomes available; Playwright is intentionally not added to Python dependencies.

Next add stable accessible selectors with Agent 2 and test form submission,
explicit count unchanged after age changes, loading/disabled submit, accepted
reading pages, RTL DOM direction and logical order, 422 field errors versus
quality errors, 503/504 recovery, rejected-draft absence and keyboard navigation.
Do not implement selectors against an imagined UI. Save/export/persistence need
implemented contracts first. Current smoke cannot establish any of those flows.
