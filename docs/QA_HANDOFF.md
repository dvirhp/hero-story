# StoryForge AI independent QA handoff

Updated 2026-11-05 (Asia/Jerusalem). Agent 4's expanded product QA preparation;
this replaces the earlier foundation-only handoff. No conversation context is
needed to reproduce the work or understand its limits.

Latest frontend/UX assignment: see [FRONTEND_UX_QA_REPORT.md](FRONTEND_UX_QA_REPORT.md),
[FRONTEND_E2E_TEST_MATRIX.md](FRONTEND_E2E_TEST_MATRIX.md) and the concise
[Agent 2 handoff](FRONTEND_AGENT2_QA_HANDOFF.md). Independent immutable frontend
exports verified delivered 1647d71 (74 unit/12 browser passes), reader bd40358
(75 unit/14 browser passes), then expanded b09f54b (87 unit passes/build passed).
Latest upstream browser run: 5 passed/13 failed; twelve failures identify the new
header cart axe issue and one transient mobile reader connection failure passed
an isolated rerun. A later full rerun was blocked by occupied port 5186 before tests.

Latest independent regression on a separately owned preview: 17 functional passes,
eight finding probes inspected/present, one axe sweep inspected, zero harness
failures or unverified cases. All 22 axe scenarios report the header accessible-name
regression. Screenshots/results are under docs/qa-screenshots/frontend-ux-latest;
earlier evidence remains under frontend-ux. P1s: Hebrew cover binding and cover
title contrast. Local avatar and simulated format/cart/checkout/confirmation now
work; no real commerce, frontend/API/PostgreSQL or secure account/session integration
is verified. Later uncommitted Agent 2 changes remain excluded and need a fresh run.

Subsequent engine diagnosis on the same date: see
[AI_ENGINE_QA_REPORT.md](AI_ENGINE_QA_REPORT.md). Seventeen additional offline
characterization probes reproduce one P2 local fixture distribution defect and
document known semantic-quality gaps. The selected regression run passed 449
cases (including those 17); diagnostics snapshot rerun passed 42. No failed or
skipped tests. These selected runs do not replace the earlier 789-case full-run
evidence below or claim a fresh complete-suite run. The earlier no-confirmed-defect
statement describes the product-strategy phase; the local fixture defect is the
new finding, with exact reproduction and owner recommendations in the report.

## Location, source versions and ownership

QA worktree: `C:\Users\dvir3\storyforge-qa`.
Branch: `feature/storyforge-qa-foundation`. Clean baseline for this expansion:
`4dca2ac` (QA handoff), after foundation implementation
`136296c83f46cd8305b0580b6a29a9598a96f5a2`.
Production baseline remains `5ae24e9c14dee82a1aca3e6eda45dff88fe4aebc`, the
explicit page-count v2 implementation. Source repository is
`C:\Users\dvir3\OneDrive\Desktop\heroStory`.

Independent component snapshots inspected/executed without merging:

| Component | Commit | Evidence / limit |
| --- | --- | --- |
| Agent 1 backend diagnostics | `7105be940c4381fcce2d74813681df6afa631474` | Read PROVIDER_DIAGNOSTICS.md; ran 42 diagnostic tests in exported snapshot |
| Agent 2 frontend | `c2b72c2d412b9bb7038fd8a9a746614ea5c92a73` | Read FRONTEND_HANDOFF.md; ran component tests, build and browser scenarios in exported snapshot |
| Agent 3 persistence | `73ac933cd3d4217f2b77918cf650b0a2ad862458` | Read PERSISTENCE_HANDOFF.md only; no independent PostgreSQL rerun |

Agent 2 has uncommitted product-foundation work; Agent 3 has uncommitted product
architecture/schema/API proposals. These were not copied into tested snapshots.
Agent 3's mutable API_CONTRACTS.md proposes v3 and explicitly supersedes the older
unapproved save=true suggestion. Neither is an approved executable API contract.
Do not implement tests against proposed DTOs as though they were settled.

Only QA tests, QA tooling and docs are changed on this branch. Other worktrees,
branches, production code, application dependencies and shared config are untouched.
No merge, cherry-pick, push, deployment, real credential read, billing change,
package download or live AI request was performed. Scratch source exports are
ignored under `qa/.local/`; they are not integration merges.

## Deliverables and test architecture

- [QA_STRATEGY.md](QA_STRATEGY.md): risk-based strategy for AI/template/manual,
  API/database/security/browser layers and recommended release gates.
- [QA_TEST_MATRIX.md](QA_TEST_MATRIX.md): per-scenario level, priority, explicit
  automation status, dependencies and actual execution; blocked is not a pass.
- [QA_HUMAN_REVIEW.md](QA_HUMAN_REVIEW.md): separate native-language editorial
  rubric. Automated tests do not prove literary quality or educational accuracy.
- `tests/test_qa_v2_http.py`: now 39 independent HTTP cases, using real FastAPI,
  lifespan/dependencies, normalization, LangGraph, ledger and quality gate with
  actual scripted FakeProvider. New expansion adds concurrent cross-request
  privacy/ledger isolation and transient planner recovery within three attempts.
- `tests/fixtures/qa_v2_requests.json`: five synthetic bilingual briefs across
  age bands and story types; accents, Hebrew niqqud, multiword names, emoji and
  ordered targets. Existing Roy fixture supplies full 27-page alphabet coverage.
- `qa/prepare_snapshot.py`: pins committed frontend/diagnostics exports into
  QA scratch space. Frontend installed dependencies are copied, never symlinked
  or modified in Agent 2's worktree. Existing snapshots are not overwritten.
- `qa/e2e/browser-regression.mjs`: executed Playwright browser API runner with
  eight real-Chromium scenarios against a local built frontend **mock service**.
- `qa/e2e/playwright.config.ts` and `local-smoke.spec.ts`: earlier optional
  Playwright Test foundation, still unexecuted. Do not confuse it with the
  executed standalone runner. `qa/e2e/README.md` contains startup commands.

HTTPX ASGITransport exercises the actual application in-process without TCP/DB.
Existing adapter tests use real SDK serialization over mocked HTTP transports and
dummy keys. Existing pytest-socket guard disables network during test execution;
the Windows event loop is initialized first to permit its local socket pair.
Frontend Vitest uses jsdom/mocked service/fetch; browser execution uses real React,
Chromium and a loopback preview server, with no backend/database requests.

## Commands and environments

Verified on Windows, Python 3.13.3, Node 22.16.0, npm 10.9.2, Playwright 1.62.0
and cached Chromium build 1228. No tools were installed during this work.

From the QA worktree in PowerShell:

```powershell
$env:PYTHONPATH = 'C:/Users/dvir3/storyforge-qa/src'
& C:/Users/dvir3/OneDrive/Desktop/heroStory/.venv/Scripts/python.exe -m pytest -q
& C:/Users/dvir3/OneDrive/Desktop/heroStory/.venv/Scripts/python.exe -m pytest tests/test_qa_v2_http.py -q
```

This reuses the existing interpreter/dependencies without changing the environment.
PYTHONPATH is mandatory to test isolated source instead of another editable branch.
For a new environment, provision the committed locked dependencies first; that
installation may require network, but test execution needs no credentials or AI.

Component snapshots, when not already prepared:

```powershell
python qa/prepare_snapshot.py frontend
python qa/prepare_snapshot.py diagnostics
$env:PYTHONPATH = 'C:/Users/dvir3/storyforge-qa/qa/.local/diagnostics-snapshot/src'
& C:/Users/dvir3/OneDrive/Desktop/heroStory/.venv/Scripts/python.exe -m pytest qa/.local/diagnostics-snapshot/tests/test_provider_diagnostics.py -q
# Restore QA source for subsequent baseline tests:
$env:PYTHONPATH = 'C:/Users/dvir3/storyforge-qa/src'
Push-Location qa/.local/frontend-snapshot/frontend
npm ls --depth=0
npm test
npm run build
node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4184 --strictPort
```

Preview runs in foreground; use a second QA-root terminal for the browser runner:

```powershell
$env:STORYFORGE_PLAYWRIGHT_MODULE = 'C:/Users/dvir3/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright/index.mjs'
$env:STORYFORGE_CHROMIUM = 'C:/Users/dvir3/AppData/Local/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-win64/chrome-headless-shell.exe'
node qa/e2e/browser-regression.mjs
```

Adjust tooling paths for another machine. Browser tests block external requests,
disable service workers and save no screenshots, traces, video or child artifacts.
They assert no v1/v2/v3 API call occurs, documenting the demo boundary. Stop only
the preview server you started; no persistent background service is required.

## Actual results

| Run | Passed | Failed | Skipped | Meaning |
| --- | --- | --- | --- | --- |
| Initial expanded-session full QA suite | 787 | 0 | 0 | 154.78 seconds; baseline plus original 37 QA cases |
| Final complete QA regression | 789 | 0 | 0 | 129.79 seconds; all final QA tests included in one run |
| Final focused QA HTTP suite | 39 | 0 | 0 | 4.19 seconds, includes two new expansion cases |
| Diagnostics committed snapshot | 42 | 0 | 0 | 67.25 seconds; offline mocked upstream diagnostics, not merged baseline |
| Frontend committed snapshot Vitest | 40 | 0 | 0 | 3 files, 10.25 seconds; React/jsdom with mocks |
| Frontend TS/Vite build | Passed | 0 | n/a | Built from pinned source; npm ls --depth=0 also passed |
| Final Chromium demo regression | 8 | 0 | 0 | Actual browser with mocked service, no backend or database |
| PostgreSQL/API-to-storage/full E2E | Not executed | n/a | n/a | Remains blocked; no invented pytest skips |

The final complete QA regression includes both new cases. Focused/full runs
overlap; do not sum them into unique case counts.
Diagnostics and frontend are separate component snapshots, not one assembled stack.
No line/branch coverage tool is installed; there is no numerical coverage claim.

Initial browser harness setup failed because PowerShell/npm forwarding produced an
incorrect preview command. A direct Vite command fixed it. Two initial assertions
also assumed initial focus and visibility of collapsed demo controls; the runner
was corrected to follow the actual DOM contract and rerun successfully. Those were
QA harness issues, not product defects or unresolved failed tests.

## Coverage, confirmed defects and ranked risks

Passed AI contracts include exact user count independent of age, page ordering,
schema/quality rejection, Roy's ordered Hebrew targets, Unicode/direction,
strict malformed input, provider failure/retry capacity, reservation accounting,
deadlines/cancellation and safe errors. New concurrent requests have separate
names, counts, UUIDs and fresh two-attempt ledgers; captured logs omit both names.
Transient planner failure recovers with exactly one retry plus writer, total three.

Passed real-browser demo checks cover four landing widths, reader boundaries,
page count surviving age edit, Hebrew logical text/niqqud and mixed directions,
invalid-field focus, skip-link keyboard activation, cancellation/no stale reader,
HTML-like name as text, no persisted brief after refresh and demo error/empty states.
These are not API integration, save/reopen or semantic story tests.

**Confirmed production defects: none established by these executions.** There are
therefore no production defect reproduction steps to invent. To reproduce a future
finding, use the named matrix scenario and pinned source; record sanitized expected/
actual values, command and call/row counts, never real child data or credentials.

Remaining risks ranked by impact:

1. **P0: ownership/authentication and privacy policy absent.** Unauthorized/cross-user
   books and assets cannot be verified. No production or real-child-data readiness.
   Retention/deletion/backups/logging review remains outstanding.
2. **P0: saved success/atomicity integration absent.** Engine HTTP does not compose
   with persistence; no full browser/API/PostgreSQL failure or ambiguous-commit proof.
   No partial saved-book claim, durable POST idempotency or safe regeneration retry.
3. **P0: template execution and source integrity unimplemented.** Placeholder/asset
   safety, release sealing, version pinning and cross-user source isolation remain
   prepared specifications until contracts and code exist.
4. **P1: common Book/editor/catalog contracts unsettled.** Manual concurrency,
   exact reorder, finalization, preview/save parity and library are not executable.
5. **P1: frontend is demo-only.** Actual service selection, same-origin routing,
   HTTP cancellation/error recovery and server count-policy reconciliation untested.
6. **P1: literary/developmental/education quality unproven.** Synthetic filler and
   literal/script checks cannot certify fluent language, facts, safety or age fit.
7. **P1: coverage outside local environment.** No independent PostgreSQL runtime,
   load/failover testing, deployed logs, full accessibility, screen-reader review,
   additional languages, illustration/export or dependency/history security audit.

Agent 3 reports 14 real PostgreSQL cases and 773 combined cases in its handoff.
Those are explicitly third-party handoff evidence, not this QA execution. That
repository proves foundation persistence behavior only, not full product Book flow.

## Integration dependencies and continuation

Agent 1 owns diagnostics/reliability; Agent 2 owns frontend; Agent 3 owns persistence,
domain and API design. No edits to their code are authorized by this handoff.

1. Obtain reviewed/approved product contracts and source commits from Agent 3.
   Reconcile v3 proposal with old save=true discussion; do not assert either as live.
2. Obtain Agent 2's committed catalog/template/manual/library UI and reviewed local
   HTTP composition. Keep the first integration explicitly Fake Provider only.
3. Provision a new QA-owned disposable local PostgreSQL database before independent
   migration/repository tests; never downgrade another agent's database or volume.
4. Execute unmocked local browser-to-API-to-PostgreSQL workflows after composition
   exists. Verify persisted/reopened ordered content, both languages, all three modes,
   quality/provider/storage failures, atomic rollback and concurrent revision conflict.
5. Add authorization/asset/retention tests when actual policies and identities exist.
   UUIDs, Origin and supplied user headers do not establish ownership.
6. Run full integrated regression and record evidence; complete native-language
   editorial and accessibility review before release-readiness claims.

Recommended gates: approved contracts/policies; zero unresolved P0/P1 defects; all
critical matrix rows executed and passing; real local Fake-only E2E for all modes;
disposable PostgreSQL migration/rollback, security/owner checks; native editorial
approval and accessibility review. Current state does not meet complete-product gates.

For final QA commit identifiers, run `git log -3 --format="%H %s"` in this worktree.
Expansion implementation commit: `5b8fe1a0428bf909ce9157034da947d6b0d5b948`.
The document's own commit is identified by `git log -1 --format=%H -- docs/QA_HANDOFF.md`.
No commit can embed its own hash. Stop after delivery for review; no merging or
deployment is part of continuation without further instruction.
