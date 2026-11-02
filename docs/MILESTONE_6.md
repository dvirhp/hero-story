# Milestone 6 completion report

Gemini integration is implemented and tested offline. Fake remains the default, OpenAI is preserved, and no live API request was executed. The four-node LangGraph and FastAPI routes retain their existing responsibilities. Stop after Milestone 6; live Gemini execution and Milestone 7 require separate approval.

## Implementation and files

New source modules:

- `llm/gemini_provider.py`: official async SDK client construction/cleanup, one-call adapter, strict response validation, safe error/refusal handling, retry-delay and usage normalization.
- `llm/gemini_schema.py`: pure JSON-schema projection with singleton enums; domain schemas remain unchanged.

Modified source modules: `config.py` adds Gemini selection; `llm/configuration.py` separates common credential validation from vendor names; `orchestration/budget.py` selects pure input reservation policies outside nodes; `orchestration/engine.py` applies the existing capacity/pricing checks to both real providers; `api/configured.py` reads only the selected key and composes/closes the selected adapter. `pyproject.toml`/`uv.lock` add `google-genai>=2.34,<3`, resolved to **2.34.0**. OpenAI's implementation, provider protocol, prompts, domain contracts, quality rules and API routes are unchanged.

New tests: `gemini_helpers.py`, `test_gemini_provider.py`, `test_gemini_integration.py`. New examples: `gemini-smoke-runtime.json` and `gemini-smoke-request.en.json`. New docs: `GEMINI.md` and this report. Updated `.env.example`, README, AGENTS, Product Spec, Architecture, AI Design, Roadmap, Orchestration, API, Providers and Extensibility documentation.

## Architecture and accounting

The adapter uses `client.aio.models.generate_content` with existing Planner/Writer prompts, native JSON schema, bounded output tokens and per-call timeout. It supports distinct stage model IDs, capacities and tariffs. The configured factory selects fake/OpenAI/Gemini through server configuration, never user story input. Gemini uses `GEMINI_API_KEY`; the default fake factory ignores credential environment configuration. There is no dotenv discovery, model discovery, token-count API probe or credential validation call.

SDK HTTP retries use one total attempt. Automatic continuation and automatic function calling are disabled. All graph recovery and quality rewriting share the existing maximum three attempts and one rewrite. Numeric/date Retry-After and Google RetryInfo delays respect the request deadline. Both SDK pools close during lifespan shutdown/startup failure; custom test transports are explicitly caller-owned. Sanitized errors never expose raw Google diagnostics, credentials, prompts, rejected drafts or thought text.

Normalized output usage includes candidate plus thought tokens; thinking is recorded as a subset, cached input as a subset of prompt tokens. Totals are reconciled. Missing/inconsistent usage stays unknown; missing prices yield independent unknown cost. Input/schema UTF-8 reservations and declared overhead are conservative engineering estimates, not exact Gemini tokenization or invoice guarantees. Output caps include thinking. Writer affordability uses its own tariff before starting a planner call. Details and limitations are in [GEMINI.md](GEMINI.md).

## Tests and builds

**541 passed, 0 failed** on **Python 3.12.16** and **3.13.3** on Windows. All **450 existing tests are unchanged**. The 91 new cases cover both stages, Hebrew/English and all five age profiles, schemas, incomplete/malformed output, refusals and unsafe output, transport/auth/rate-limit failures, disabled retries/continuation/tools, usage/cache/thought accounting, unknown pricing, deadlines/cancellation, shared budgets, one quality rewrite, configuration, secret redaction, FastAPI dependency override and lifecycle cleanup. The prepared smoke JSON files also run through the entire pipeline using a mock transport.

Runtime warnings were treated as errors during full verification. SDK cleanup finalizers are drained before the guarded test loop closes; no warning suppression is added. Tests block network sockets and use synthetic keys plus HTTPX mock/ASGI transports. The initial additional RetryInfo test exposed an SDK attribute mismatch; the adapter was corrected and the complete suites rerun successfully.

Source distribution and wheel builds passed. An isolated installed-wheel import check confirms `site-packages` usage on Python 3.12.16; the full **541-test** suite also passes against that wheel. Build outputs and caches remain ignored. No listening server or real provider request is used by automated tests.

## Exact PowerShell commands

From the repository root:

```powershell
py -m venv .tools
.\.tools\Scripts\python.exe -m pip install uv==0.13.6
.\.tools\Scripts\uv.exe sync --locked
.\.venv\Scripts\python.exe -m pytest -q -W error::RuntimeWarning
.\.tools\Scripts\uv.exe run --python 3.12 --isolated --locked python -m pytest -q -W error::RuntimeWarning
.\.tools\Scripts\uv.exe build
.\.tools\Scripts\uv.exe run --no-project --isolated --python 3.12 --with .\dist\storyforge_ai-0.1.0-py3-none-any.whl --with pytest==9.2.0 --with pytest-socket==0.8.1 python -m pytest -q -W error::RuntimeWarning
```

Safe default server command:

```powershell
.\.venv\Scripts\python.exe -m uvicorn storyforge.api.app:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

No key is required for these setup/test/fake commands. The optional **live** setup, single POST and environment cleanup commands are documented separately in [GEMINI.md](GEMINI.md); do not execute them without approval.

## Proposed first live run and remaining decisions

The concrete proposal uses `gemini-3.5-flash-lite` for Planner and Writer, a synthetic English newborn brief, four short read-aloud pages, up to 8,000 input tokens and 800 output tokens per attempt, three attempts maximum, 26,400 aggregate reservation units, and a USD 0.015 request ceiling. At the reviewed standard text tariff, the two-call worst-case planning estimate is USD 0.0088 and three-call estimate USD 0.0132; actual charges remain unknown before execution. The model is listed for free-tier input/output, but this account's eligibility and remaining quota were not checked. Prices, supported functionality, terms and exact commands are linked in the [live proposal](GEMINI.md). No assumption of free use is made.

Remaining decisions: approval for that live POST; account/model access, tier/quota and privacy review; measured story/read-aloud quality and framing estimates; future provider comparison and fallback policy; language registry, pronouns/segmentation and native evaluation before any additional language; release requirements and provisional developmental-profile tuning. Current contracts still support only Hebrew/English, with no new language restrictions. Full multilingual support and Claude remain outside scope. No unnecessary infrastructure or scope deviation was introduced.

## Git and stop boundary

Branch: `feature/milestone-6-gemini`, created from the clean completed Milestone 5 branch. Implementation commits in order:

1. `77e645a` — bounded async adapter, schema/configuration foundation, accounting and SDK transport tests.
2. `349b108` — configured application composition, integration tests and synthetic smoke configuration.
3. Final documentation commit follows these; `git log --oneline df8fce3..HEAD` lists the complete sequence.

All prior history and existing author settings are preserved. No real Gemini/OpenAI API calls, billing changes, credential exposure, push, merge, deployment, Claude integration, extra language or Milestone 7 work occurred. Actual local keys were not needed or requested. The user may review the completed milestone before separately approving any live request.
