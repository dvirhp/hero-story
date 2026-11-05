# Deferred browser integration

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
