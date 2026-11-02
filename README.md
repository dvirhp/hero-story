# StoryForge AI

A personalized children's story engine supporting Hebrew and English from birth. Age uses strict nonnegative integer `age_months`, including newborns at zero; no upper age cutoff is imposed.

**Milestones 1–4 are implemented: offline contracts, validation/quality rules, bounded LangGraph execution and a local FastAPI application.** Default HTTP generation uses synthetic fixture text, not a real LLM. Milestone 5 and later require approval.

## Implemented foundation

- Python 3.12+ package with strict, immutable Pydantic v2 contracts for requests, briefs, plans, stories, results, quality reports and usage records.
- Five provisional bands in [profiles.v1.json](src/storyforge/development/profiles.v1.json), validated for continuous coverage from zero through an open-ended older-child band. Hebrew/English requirements can be configured independently.
- Pure age/language resolver and immutable profile snapshots. Page/word limits are hard structural checks; sentence length, vocabulary, repetition and developmental guidance are soft product hypotheses, not scientific standards.
- Language-tagged explicit pronoun forms and agreement. Absence never infers gender from a name. Curated presets and broader Hebrew agreement support remain open.
- Validated offline settings, asynchronous provider protocol and deterministic scripted fake supporting success, malformed output, refusals, transient errors, unknown usage and simulated timeouts.
- Offline pytest tests with network sockets blocked during tests. Windows asyncio's internal loop socket pair is created before per-test guards; provider execution remains guarded.
- Pure `normalize_request` resolves an immutable brief from a validated request and rejects prohibited controls/directives without rewriting names, Unicode or pronouns.
- Pure `assess_story` checks schema, metadata, personalization, profile lengths, controls, coarse script evidence and narrow dangerous directives. Existing `QualityReport` distinguishes repairable/terminal failures from advisory observations.
- One compiled four-node LangGraph with typed immutable state, versioned language-aware prompts, shared attempt/token/cost reservations, conditional recovery, cancellation and timeout handling. Only planner/writer invoke the fake provider.
- A FastAPI factory with lifespan configuration, async dependency injection, health and generation endpoints, sanitized errors and request-scoped cancellation cleanup. No provider calls occur at import/startup.

Domain models and adapters do not depend on provider SDKs, FastAPI or LangGraph. The orchestration package owns the LangGraph dependency. `Story.validate_for(brief)` checks structural/length constraints only; it is not a quality or safety gate. Fake scripts are fixtures, not generated literature. The fake supplies scripted usage/latency and does not retry; the engine enforces the shared budgets. An optional sanitized quality report on provider failures preserves terminal safety findings from schema-invalid outputs without retaining raw responses.

`assess_story` accepts a `Story`, raw JSON or JSON-compatible mapping and returns sanitized issues without draft text. A passing report means only that the configured deterministic hard checks passed. Fewer than 20 eligible body letters (configurable), including zero, produces an explicit non-blocking `LANGUAGE_EVIDENCE_INCONCLUSIVE`; it does not establish the story's language. With enough evidence, the default target-script minimum is 80%. Short baby refrains and intentional repetition are allowed. Soft sentence/vocabulary measurements do not prove developmental fit; narrow directive matching does not prove safety. See [implemented behavior, issue codes and limitations](docs/VALIDATION_AND_QUALITY.md).

## Windows PowerShell setup

Run from the repository root with Python 3.12+ installed. No activation or execution-policy change is required. Internet access is needed to install dependencies, never to run the tests.

```powershell
py -m venv .tools
.\.tools\Scripts\python.exe -m pip install uv==0.13.6
.\.tools\Scripts\uv.exe sync --locked
.\.venv\Scripts\python.exe -m pytest
```

`uv.lock` records resolved versions and artifact hashes; `--locked` fails if project metadata disagrees with it. The build backend is pinned in `pyproject.toml`. To select an interpreter explicitly, replace the sync command with:

```powershell
.\.tools\Scripts\uv.exe sync --locked --python 3.12
```

Subsequent tests need only:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The default command inside the selected environment is `python -m pytest`. No environment variables, API keys, provider credentials or paid calls are needed. Settings use `AppSettings()` or validation of explicitly supplied data; they do not read the environment.

Milestone 1 verification: **115 passed, 0 failed** on Windows with Python 3.12.16 and 3.13.3. Wheel/source builds and an isolated installed-wheel profile-resource/import smoke check also passed. These checks establish contracts and offline behavior, not developmental or literary quality.

Milestone 2 verification: **270 passed, 0 failed**, including the unchanged 115 Milestone 1 tests, on Windows with Python 3.12.16 and 3.13.3. No dependencies were added; pure validation/assessment tests make no provider calls, require no credentials and run with network sockets blocked.

Milestone 3 adds LangGraph and 60 execution/foundation cases, preserving all 270 earlier tests. **330 passed, 0 failed** on Windows/Python 3.12.16 and 3.13.3. Wheel/source builds passed. The complete suite remains offline; no real LLM provider SDK or credentials are used.

Milestone 4 verification: **393 passed, 0 failed** on Python 3.12.16 and 3.13.3, preserving all original 330 tests unchanged. The 63 new cases cover HTTP contracts, injected providers, sanitized failures, cancellation, lifecycle and documented JSON examples. HTTP tests use in-process ASGI transport with sockets blocked; no listening server is needed. Wheel/source builds and isolated installed-wheel API smoke checks passed.

## Local HTTP API

After synchronization, start the development server in the foreground:

```powershell
.\.venv\Scripts\python.exe -m uvicorn storyforge.api.app:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

In a second PowerShell window at the repository root:

```powershell
Start-Process 'http://127.0.0.1:8000/docs'
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health'

$heBody = Get-Content -Raw -Encoding UTF8 .\docs\examples\story-request.he.json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/v1/stories/generate' -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($heBody))

$enBody = Get-Content -Raw -Encoding UTF8 .\docs\examples\story-request.en.json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/v1/stories/generate' -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($enBody))
```

Use Ctrl+C to stop the server. The [Hebrew newborn](docs/examples/story-request.he.json) and [English older-child](docs/examples/story-request.en.json) requests have synthetic names and explicit pronouns. UTF-8 bytes preserve Hebrew on Windows PowerShell 5.1. No `.env`, API key, account or paid service is required. Access logging is disabled by the command. Swagger UI may need internet for its default CDN assets; the API, OpenAPI JSON and tests do not.

`POST /v1/stories/generate` returns the existing approved `GenerationSuccess` or a sanitized `GenerationFailure`, with `X-Request-ID` and `Cache-Control: no-store`. Invalid input is 422; input policy rejection 400; provider output/refusal/unsafe output 502; availability or budget exhaustion 503; deadline 504; internal failure 500. The existing `422 QUALITY_REJECTED` remains distinct from invalid input by code/stage. Observed cancellation has a best-effort non-standard 499 response, which a disconnected client usually cannot receive.

The API calls the existing engine, without duplicating retries, budgets or quality rules. The default request-local fixture adapter delegates to `FakeProvider`; it does not fulfill creative guidance semantically. Disconnect detection depends on ASGI events and cooperative cancellation; no detached generation job is created. See [API contracts, response examples, injection and limitations](docs/API.md).

## Local fake generation

```powershell
.\.venv\Scripts\python.exe -m storyforge.demo --language he --age-months 0
.\.venv\Scripts\python.exe -m storyforge.demo --language en --age-months 180
```

The demo creates synthetic fixtures, runs the graph and prints metadata only. Normal success uses two provider attempts; all retries and the single allowed quality rewrite share a maximum of three. A planner retry must leave a writer slot. Terminal safety findings never trigger a rewrite. Failed/unapproved drafts are never returned.

Default time limits: 30 seconds per attempt and 90 overall. Token caps are 8,000 input / 1,200 planner output / 3,000 writer output. Fake budget defaults use 33,000 aggregate reservation units, a documented UTF-8-byte input bound and a zero synthetic tariff; they do not establish real token counts or pricing. Unknown usage remains unknown with conservative reservations held. Real pricing, model capacity and tokenizer validation remain Milestone 5. Full state, recovery and cancellation policies are in [ORCHESTRATION.md](docs/ORCHESTRATION.md).

For Python 3.12 verification without changing `.venv`:

```powershell
.\.tools\Scripts\uv.exe run --python 3.12 --isolated --locked python -m pytest -q
```

Build an installable wheel and source distribution:

```powershell
.\.tools\Scripts\uv.exe build
```

Deliberate dependency updates use `uv.exe lock --upgrade` followed by lockfile review and tests; ordinary setup uses `--locked`. Setup behavior follows the [uv locking documentation](https://docs.astral.sh/uv/concepts/projects/sync/).

## Modules and plans

| Location | Responsibility |
| --- | --- |
| `src/storyforge/domain/` | Strict provider-independent contracts and context-dependent plan/story validation |
| `src/storyforge/development/` | Versioned JSON profiles, configuration validation, explicit loader and pure resolver |
| `src/storyforge/config.py` | Validated fake-only settings and future execution limits |
| `src/storyforge/llm/` | Async typed protocol, success/failure contracts and scripted fake |
| `src/storyforge/validation/` | Pure normalization, input policy checks and sanitized errors |
| `src/storyforge/quality/` | Versioned configurable rules, Unicode/text helpers and deterministic quality assessment |
| `src/storyforge/orchestration/` | Compiled graph, typed state, request-local attempt journal and synthetic budget accounting |
| `src/storyforge/prompts/` | Versioned planner/writer instructions and serialized untrusted data |
| `src/storyforge/demo.py` | Offline fixture-generation command; prints metadata only |
| `src/storyforge/api/` | Application factory, dependencies, HTTP routes, sanitized errors and disconnect cleanup |
| `src/storyforge/llm/fixtures.py` | Shared synthetic fixture builder and local default adapter delegating to FakeProvider |
| `tests/` | Original 270 tests plus bounded execution, deadlines, cancellation, budgets and recovery |

- [Product scope and acceptance criteria](docs/PRODUCT_SPEC.md)
- [Architecture and contracts](docs/ARCHITECTURE.md)
- [AI strategy and budgets](docs/AI_DESIGN.md)
- [Roadmap and offline test matrix](docs/ROADMAP.md)
- [Implemented validation and quality policies](docs/VALIDATION_AND_QUALITY.md)
- [Implemented orchestration and Git workflow](docs/ORCHESTRATION.md)
- [Implemented HTTP API and PowerShell examples](docs/API.md)
- [Coding agent rules](AGENTS.md)

Implemented flow: HTTP/Pydantic validation -> engine -> Input Validation -> Story Planner -> Story Writer -> Quality Gate, with bounded conditional recovery. No supervisor, database, frontend, RAG, Docker or real provider is included. Next is Milestone 5's first real provider adapter, only after approval. Profile refinement, older-child subdivisions, pronoun presets, script-threshold calibration, reviewed safety-rule expansion, provider/model, real pricing ceiling and human evaluation/release criteria remain open.

Git work is local on `feature/milestone-4-fastapi`, branched from completed Milestone 3. Use small tested commits; inspect `git status` and staged diffs before committing. Existing author/credential settings are preserved. No remote, push, merge or deployment is configured or authorized. Generated ZIPs under `new/`, environments, secrets, caches and builds are ignored.
