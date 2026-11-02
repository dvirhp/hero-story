# Milestone 5 completion report

Implemented OpenAI integration using the official async SDK; fake remains the default. No major architectural change was necessary. Planner/Writer can select separate models, capability declarations and tariffs. The four graph nodes and quality responsibilities remain unchanged. Worldwide languages and additional providers are documented future work, not newly enabled languages/adapters.

## Files

New modules: `llm/configuration.py` (secret/capability contracts), `llm/schema.py` (strict schema projection), `llm/openai_provider.py` (one Responses call and normalized errors/usage), `api/configured.py` (validated opt-in runtime composition and client lifecycle).

Updated modules: `config.py`, `domain/generation.py`, `llm/protocol.py`, `orchestration/budget.py`, `orchestration/engine.py`, `orchestration/state.py`, `api/dependencies.py`. Updated `pyproject.toml`/`uv.lock` include the official SDK. Domain/protocol contracts contain no SDK types.

Four new test modules: `test_openai_configuration.py`, `test_openai_provider.py`, `test_real_accounting.py`, `test_openai_integration.py`. All 393 preceding tests are unchanged. New documentation: `PROVIDERS.md`, `EXTENSIBILITY.md`, this report, `.env.example`, intentionally invalid `examples/openai-runtime.template.json`. README, AGENTS and existing planning/architecture/API documents now link the current behavior and future proposals.

## Runtime behavior

The normal factory ignores environment credentials. Explicit live composition requires `STORYFORGE_ALLOW_PAID_CALLS=true`, `STORYFORGE_CONFIG`, and `OPENAI_API_KEY`; it never probes during startup. Real settings without an explicitly injected provider fail rather than silently producing fake output. Secrets are excluded from serialization/repr, graph state and public errors.

Remote strict JSON schema is a projection; local full Pydantic/profile/quality validation remains authoritative. Adapter retries are disabled. Refusals, auth/configuration errors and unsafe output are terminal; transient/schema recovery uses the existing shared three-attempt budget. Retry-After cannot exceed the overall deadline. Cancellation preserves conservative reservations and cannot guarantee remote requests are unbilled.

Reported input/output tokens and cached/reasoning subsets are normalized without double-counting. Missing usage stays unknown. Missing prices leave cost unknown, independently exposed by `has_unknown_cost`. Positive versioned reservation tariffs and an approved positive aggregate ceiling are mandatory for real execution. Future writer capacity uses the writer's own tariff. UTF-8 byte/framing reservations are configurable conservative estimates, not an exact tokenizer or billing guarantee; verify model declarations before paid use.

## Verification and exact commands

Windows Python **3.13.3: 450 passed, 0 failed**. Python **3.12.16: 450 passed, 0 failed**. This includes all original 393 tests and 57 new cases. Tests block sockets and use HTTPX mock/ASGI transports with dummy, non-credential strings. Both languages cover all five developmental profiles with distinct stage models, plus failures, retries, accounting, API override, lifecycle and cancellation paths.

```powershell
py -m venv .tools
.\.tools\Scripts\python.exe -m pip install uv==0.13.6
.\.tools\Scripts\uv.exe sync --locked
.\.venv\Scripts\python.exe -m pytest -q
.\.tools\Scripts\uv.exe run --python 3.12 --isolated --locked python -m pytest -q
.\.tools\Scripts\uv.exe build
.\.tools\Scripts\uv.exe run --no-project --isolated --python 3.12 --with .\dist\storyforge_ai-0.1.0-py3-none-any.whl --with pytest==9.2.0 --with pytest-socket==0.8.1 python -m pytest -q
```

Source distribution and wheel build successfully. The isolated installed wheel passes the full 450-test suite; a separate import check confirms `storyforge` loads from `site-packages`, not the source tree. Generated build outputs remain ignored. Optional live setup/smoke commands and warnings are documented in [PROVIDERS.md](PROVIDERS.md); none was executed.

## Git, limitations and stop boundary

Local branch: `feature/milestone-5-real-llm`, from completed Milestone 4. Implementation commits in chronological order: `88f9ec7`, `c411612`, `dfea20e`, `b4ba448`; the final documentation commit follows them. Existing author settings and history were preserved. No remote, push, merge or deployment occurred.

No scope deviations beyond the user's explicitly requested stage-model extensibility and future-language/provider documentation. Only fake/OpenAI and Hebrew/English execute today. No real model quality, latency, capacity declaration or current tariff has been validated by a live call. The input estimate needs model-specific verification; unknown prices remain unknown and declared reservation ceilings are not guaranteed invoices. Automated hard checks do not establish fluency, comprehensive safety, developmental fitness or read-aloud quality.

Remaining decisions: stage model IDs, verified capabilities/overhead, actual rates and spend ceilings; provider comparison/privacy/fallback policy; additional languages/locales, segmentation/counting and explicit agreement contracts; human evaluation/release thresholds; older-child subdivisions and provisional profile tuning. See [extension review](EXTENSIBILITY.md) and [proposed roadmap](ROADMAP.md).

No real API keys were requested, read or used. No real paid API calls, billing changes, push, deployment, other provider implementations, full multilingual support or Milestone 6 work occurred. Stop after Milestone 5; later implementation and paid evaluation require separate approval.
