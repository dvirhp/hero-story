# StoryForge AI

A personalized children's story engine supporting Hebrew and English from birth. Age uses strict nonnegative integer `age_months`, including newborns at zero; no upper age cutoff is imposed.

**Milestones 1 and 2 are implemented: offline foundation, normalization and deterministic quality rules.** There is no runnable server, graph, story-generation pipeline or real provider integration. Milestone 3 and later require approval.

## Implemented foundation

- Python 3.12+ package with strict, immutable Pydantic v2 contracts for requests, briefs, plans, stories, results, quality reports and usage records.
- Five provisional bands in [profiles.v1.json](src/storyforge/development/profiles.v1.json), validated for continuous coverage from zero through an open-ended older-child band. Hebrew/English requirements can be configured independently.
- Pure age/language resolver and immutable profile snapshots. Page/word limits are hard structural checks; sentence length, vocabulary, repetition and developmental guidance are soft product hypotheses, not scientific standards.
- Language-tagged explicit pronoun forms and agreement. Absence never infers gender from a name. Curated presets and broader Hebrew agreement support remain open.
- Validated offline settings, asynchronous provider protocol and deterministic scripted fake supporting success, malformed output, refusals, transient errors, unknown usage and simulated timeouts.
- Offline pytest tests with network sockets blocked during tests. Windows asyncio's internal loop socket pair is created before per-test guards; provider execution remains guarded.
- Pure `normalize_request` resolves an immutable brief from a validated request and rejects prohibited controls/directives without rewriting names, Unicode or pronouns.
- Pure `assess_story` checks schema, metadata, personalization, profile lengths, controls, coarse script evidence and narrow dangerous directives. Existing `QualityReport` distinguishes repairable/terminal failures from advisory observations.

Domain models and adapters do not depend on provider SDKs, FastAPI or LangGraph. Framework integrations arrive in their approved milestones. `Story.validate_for(brief)` checks structural/length constraints only; it is not a quality or safety gate. Fake scripts are fixtures, not generated stories. The fake records synthetic latency and supplied usage; it does not tokenize, sleep, retry or enforce the future orchestrator's aggregate budget.

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
| `tests/` | Existing 115 foundation cases plus normalization, bilingual hard/soft checks, controls, directives and inconclusive evidence |

- [Product scope and acceptance criteria](docs/PRODUCT_SPEC.md)
- [Architecture and contracts](docs/ARCHITECTURE.md)
- [AI strategy and budgets](docs/AI_DESIGN.md)
- [Roadmap and offline test matrix](docs/ROADMAP.md)
- [Implemented validation and quality policies](docs/VALIDATION_AND_QUALITY.md)
- [Coding agent rules](AGENTS.md)

Future flow: Input Validation -> Story Planner -> Story Writer -> Quality Gate. No supervisor, database, frontend, RAG, Docker or real provider is included. Next is Milestone 3's bounded LangGraph engine, only after approval. Profile refinement, older-child subdivisions, pronoun presets, script-threshold calibration, reviewed safety-rule expansion, provider/model, pricing ceiling and human evaluation/release criteria remain open.
