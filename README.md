# Hero Story

Hero Story is an AI-powered personalized children's story project. Its Python story engine builds structured Hebrew or English stories from a child's age and a user-selected brief. The project also includes separate frontend, persistence and QA development branches. These components are prototypes at different stages of integration; the repository is not a production-ready service.

## Project status

- **AI engine (this branch):** FastAPI endpoints, strict Pydantic contracts, versioned developmental profiles, bounded generation and deterministic quality checks. The v2 API accepts an explicit page count; v1 remains available for compatibility. The default provider supplies synthetic fixture text, not creative AI output.
- **Providers:** OpenAI and Gemini adapters are implemented and tested with mocked transports. Live use requires explicit configuration, credentials, cost limits and authorization. Paid calls can send story data to an external provider.
- **Frontend:** `feature/storyforge-frontend-foundation` contains a React 19, TypeScript and Vite demonstration with story creation, a reader and simulated commerce. It uses mocked generation and checkout; its API and proposed product ports are not connected to the backend.
- **Persistence:** `feature/storyforge-persistence-foundation` contains an internal canonical-book model, SQLAlchemy repositories, PostgreSQL migrations and transaction boundaries. It is not integrated into the engine branch's HTTP service.
- **QA:** `feature/storyforge-qa-foundation` contains independent test harnesses, accessibility and UX reports, and screenshots. Reports record both passing checks and known issues.
- **Experimental work:** separate local evaluations and integration experiments are work in progress and are not part of this branch's committed baseline. Additional languages, real commerce, production authentication, and integrated storage remain future work.

The separate branches have diverged; checking out one does not combine their contents. See their respective handoff documents for details and limitations.

## Architecture

The engine separates provider-independent domain models, age/language profiles, prompts, adapters, orchestration, output validation and HTTP presentation. A LangGraph `StateGraph` coordinates four explicit stages:

```text
Request validation → story planner → story writer → quality gate
                           ↖ bounded retry/recovery ↙
```

Planner and writer calls use typed structured outputs through a provider protocol. A shared request budget accounts for attempts, deadlines, tokens and estimated costs, including retries and permitted rewrites. Input is treated as untrusted; invalid, unsafe or failed drafts are not returned as accepted stories. Deterministic checks cover configured structural and safety rules, but do not prove literary quality, language fluency or complete safety. Profiles and length targets are product hypotheses, not scientifically validated standards.

The default HTTP app uses a fake provider; an explicitly configured app supports OpenAI and Gemini. Logs and tracing are designed to avoid child data and raw story content. Refer to [architecture](docs/ARCHITECTURE.md), [orchestration](docs/ORCHESTRATION.md), [quality behavior](docs/VALIDATION_AND_QUALITY.md), [provider setup](docs/PROVIDERS.md) and [API contracts](docs/API.md) for boundaries and limitations.

## Setup and tests

Python 3.12 or newer is required. From the repository root, with `uv` installed:

```sh
uv sync --locked
uv run python -m pytest
uv build
```

On Windows without a globally installed `uv`:

```powershell
py -m venv .tools
.\.tools\Scripts\python.exe -m pip install uv==0.13.6
.\.tools\Scripts\uv.exe sync --locked
.\.venv\Scripts\python.exe -m pytest
.\.tools\Scripts\uv.exe build
```

Default tests use fake providers and block network sockets; no API key is required. See [CI checks and local equivalents](docs/CI.md). To run the local fake-backed API:

```sh
uv run uvicorn storyforge.api.app:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

The health endpoint is `/health`; the current generation endpoint is `POST /v2/stories/generate`. See [API examples](docs/API.md) and [v2 page-count contracts](docs/PAGE_COUNT_V2.md). The API docs UI may load assets from a CDN; the API itself does not require it.

For the optional configured provider server, [.env.example](.env.example) documents `STORYFORGE_ALLOW_PAID_CALLS`, `STORYFORGE_CONFIG`, `OPENAI_API_KEY` and `GEMINI_API_KEY`. The selected provider's key and a validated runtime configuration are required. Never commit credentials or real child data. Default startup does not automatically discover `.env`; see [OpenAI configuration](docs/PROVIDERS.md) and [Gemini configuration](docs/GEMINI.md).

To run the frontend, use the frontend branch and Node.js 22.12 or newer:

```sh
cd frontend
npm ci
npm test
npm run build
npm run dev
```

See `frontend/README.md` on that branch for browser-test prerequisites. PostgreSQL tests and migrations belong to the persistence branch and have their own setup in `docs/PERSISTENCE_HANDOFF.md` there.

## Development workflow

The project was developed across separate Git branches and worktrees for the AI engine, frontend, persistence and independent QA, with handoff documents and tests recording integration boundaries. Those branches preserve parallel development history; they are not evidence that the components have been merged into a single application. Agent orchestration in the running engine refers to the fixed generation workflow above, not a dynamic multi-agent supervisor.

- [Product specification](docs/PRODUCT_SPEC.md) · [Roadmap](docs/ROADMAP.md) · [AI design](docs/AI_DESIGN.md)
- [Offline text projection](docs/PHASE_B1.md) · [Whole-book reliability](docs/WHOLE_BOOK_RELIABILITY.md)
- [Development instructions](AGENTS.md)
