# Continuous integration

The [CI workflow](../.github/workflows/ci.yml) runs on pushes, pull requests and manual dispatch. It tests the checked-out commit; pull requests use GitHub's merge result. Jobs run in parallel with read-only repository permissions, SHA-pinned actions, disabled checkout credential persistence and cancellation of superseded runs. No secrets are configured and paid generation is disabled. The project test configuration blocks sockets; provider tests use fakes or mocked transports and dummy keys.

| Job | Checks | Scope |
| --- | --- | --- |
| Python static checks and build | Locked resolution, Ruff syntax/undefined-name rules, Python compilation, source and wheel builds | Engine and Python tests; Python 3.12 |
| Offline Python tests | Full default pytest suite | Python 3.12 and 3.13 on Linux, including fake-backed FastAPI and provider contracts |
| Runtime dependency audit | Export the complete locked runtime dependency graph and check known vulnerabilities using pip-audit | Python 3.12; queries the public advisory service |
| Frontend types, tests and build | `npm ci`, high-severity runtime dependency audit, Vitest, TypeScript and Vite build | Runs only when `frontend/package.json` and `frontend/package-lock.json` are present |

uv caches dependency downloads, and the frontend job caches npm downloads. Security advisories can change independently of source code; an audit failure should be investigated, not suppressed automatically. The audit checks known vulnerabilities, not secrets, full supply-chain integrity or application safety. The committed `uv.lock` retains artifact hashes; the audit's fully resolved export omits hashes only because `--no-deps` checks those exact listed versions without installing them.

## Run locally

Install Python 3.12 or 3.13 and uv 0.13.6. In the repository root:

```sh
uv lock --check
uv sync --locked
uv run --locked --no-sync python -m pytest
uvx --from ruff==0.14.4 ruff check --select E9,F63,F7,F82 src tests
python -m compileall -q src tests
uv build
uv export --locked --no-dev --no-emit-project --no-hashes --quiet -o /tmp/herostory-requirements.txt
uvx --from pip-audit==2.9.0 pip-audit --disable-pip --no-deps -r /tmp/herostory-requirements.txt
```

On Windows PowerShell replace `/tmp/herostory-requirements.txt` with `"$env:TEMP\herostory-requirements.txt"` in both commands. Run pytest under each installed Python version with `uv sync --locked --python 3.12` or `3.13` followed by the pytest command above. Package installation and the advisory lookup require internet access; tests do not. No production configuration, API credentials, paid requests or external service is required for the tests.

If the frontend exists in the checked-out branch, use Node 22.12 or newer:

```sh
cd frontend
npm ci --no-audit
npm audit --omit=dev --audit-level=high
npm test
npm run build
```

## Boundaries

The repository has separate, divergent engine, frontend, persistence and QA branches. This workflow runs on a branch only after that branch contains the workflow; it does not fetch other branches, mix their source trees or modify their active worktrees. After integration, the default Python suite picks up tests in that checkout; opt-in PostgreSQL tests remain skipped without `STORYFORGE_TEST_POSTGRES_URL`. They need a dedicated disposable local PostgreSQL instance and are not covered by this workflow. The QA browser harness targets a separate exported frontend, and the frontend's Playwright suite has reported existing accessibility failures; browser and cross-branch integration checks are not presented as passing CI. See the respective handoff documents for reproduction.

Ruff intentionally selects only high-confidence error rules: the existing code has no agreed project-wide formatting or Python static type-checking baseline. The frontend build runs its existing `tsc` check. No broad Python formatting or type gate is claimed. A formatter or broader type/lint policy should be adopted separately with a reviewed baseline. GitHub-hosted runtime varies with cache and network; allow roughly 5–15 minutes for the parallel jobs until observed runs provide measurements.
