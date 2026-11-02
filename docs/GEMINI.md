# Gemini integration and proposed first live smoke test

> Approved page-count update: new work uses [explicit-length v2](PAGE_COUNT_V2.md). The user supplies page_count; age controls developmental guidance and page density. Deprecated v1 keeps its original behavior. Historical milestone sections below describe v1 unless labeled v2. No live calls were made in this follow-up; Milestone 7 remains unapproved.

Milestone 6 implements Gemini only. Fake remains the default; OpenAI is preserved. No live API request was made. Neither Claude nor additional languages is implemented. The long-term worldwide-language requirement remains in [EXTENSIBILITY.md](EXTENSIBILITY.md).

## Adapter and composition

`GeminiProvider` implements the existing asynchronous `LLMProvider` protocol using Google's supported `google-genai` SDK, currently locked to 2.34.0. It calls `client.aio.models.generate_content` once per engine attempt. Domain schemas, prompts, four LangGraph nodes, routing, quality checks and HTTP routes retain their responsibilities. Planner and Writer resolve independent model IDs, capability declarations and pricing records through existing settings/runtime JSON.

`GeminiConfig` uses the common strict secret/timeout contract. `load_configuration` reads only the selected provider's key after explicit external-call opt-in. The normal `create_app` does not read configuration environment variables or discover credentials. Real settings without an injected provider fail rather than silently selecting Fake.

The configured factory constructs a client without probes during lifespan, validates capacities before serving, and closes both async and sync SDK pools on shutdown/failure. The client uses an explicit key, Developer API mode (`vertexai=False`), the official endpoint and `v1beta`, with proxy environment discovery and redirects disabled. Ambient Google provider/base-URL choices cannot override this selection. SDK-internal environment reads may still occur, but the explicit key wins; ordinary application code never falls back to `GOOGLE_API_KEY` or cloud credentials. No implicit `.env` discovery is added. Explicit Uvicorn `--env-file .env` loading is supported by the locked `python-dotenv` dependency. Custom mock HTTP transports are caller-owned and explicitly closed in tests.

## One attempt means one request

SDK HTTP retries use `HttpRetryOptions(attempts=1)` at client and per-call levels. Automatic continuation and automatic function calling are disabled; no tools or grounding are enabled. This avoids extra requests outside the shared ledger. Sampling/candidate-count parameters are omitted for compatibility with current Flash models; the default single candidate is validated locally. See Google's [parameter migration guidance](https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.6) and [SDK documentation](https://googleapis.github.io/python-genai/).

Each call receives the smaller remaining/configured deadline, both via SDK milliseconds and an asyncio timeout. Request-wide maximum remains three attempts and at most one quality rewrite. Retry-After (seconds/date) and Google RetryInfo delays are normalized and bounded by the overall deadline. There is no independent retry loop or provider fallback.

| Condition | Normalized behavior |
| --- | --- |
| Valid single STOP response | Strict local Pydantic validation, then existing profile/quality checks |
| Malformed/schema-invalid, empty, extra candidate, tool/media part, MAX_TOKENS or CONTINUATION | Retryable output failure within the shared budget; no automatic continuation |
| Prompt blocking, safety/refusal finish reason or blocked safety rating | Terminal `PROVIDER_REFUSED` |
| Locally detected unsafe output, including malformed/incomplete output | Terminal `POLICY_REJECTED`; no repair or draft leakage |
| 400/401/403/404 and other configuration/client errors | Terminal `CONFIGURATION_ERROR` |
| Connection errors, 409/429/5xx | Retryable availability failure; 408/504 are retryable deadlines |
| Timeout/cancellation | Stop local await; cancellation reaches the existing ledger-aware wrapper |

All public error messages are fixed, sanitized text. Provider messages, prompt content, raw responses, keys, reasoning and signatures are not returned or logged. Remote cancellation cannot guarantee an already accepted request is stopped or unbilled. The HTTP layer retains [its existing status mapping](API.md).

## Schemas and accounting

The pure Gemini schema projection reuses structural projection and expresses constants as singleton enums. It preserves references, required fields and forbidden extra properties. It never changes the local Pydantic contract. The adapter uses `application/json` and `response_json_schema`; native schema adherence still requires local validation. See Google's [GenerateContent structured-output guide](https://ai.google.dev/gemini-api/docs/generate-content/structured-output).

Gemini `prompt_token_count` includes cached prompt tokens. `candidates_token_count` excludes thinking, so normalized output is candidates plus `thoughts_token_count`; reasoning is recorded as a subset of that output. Totals are reconciled and invalid/incomplete usage stays unknown. Absent thought counts are treated as zero only when a complete total reconciles without them. Known counts with unknown rates still have unknown cost. Cache rates are used only for the cached subset; missing cache prices/details use the standard input rate conservatively. No category is counted twice.

Output caps include thinking, which can consume the budget before visible JSON is complete. This produces a bounded failure, not permission to increase the cap or call again outside the ledger. See [Google's token-limit explanation](https://ai.google.dev/gemini-api/docs/generate-content/thinking#token-limits-and-max_output_tokens).

Reservations count UTF-8 bytes of instructions, input JSON and Gemini's projected schema plus declared overhead, then the whole output cap. This is an engineering estimate, not an exact Gemini tokenizer or guaranteed invoice ceiling. The 1,024-unit overhead in the proposed smoke configuration is an unverified framing allowance, not a vendor standard. There are no `count_tokens` or model-discovery API probes. Known overages stop execution and remain recorded; unknown usage retains the reservation. A planner must leave capacity for the writer's own model/tariff. The existing positive reservation-rate and aggregate ceiling requirements also apply on potentially free accounts.

## Safe local setup and offline checks

From the repository root in Windows PowerShell:

```powershell
py -m venv .tools
.\.tools\Scripts\python.exe -m pip install uv==0.13.6
.\.tools\Scripts\uv.exe sync --locked
.\.venv\Scripts\python.exe -m pytest -q
.\.tools\Scripts\uv.exe run --python 3.12 --isolated --locked python -m pytest -q
.\.tools\Scripts\uv.exe build
```

Default fake server, requiring no key or environment setup:

```powershell
.\.venv\Scripts\python.exe -m uvicorn storyforge.api.app:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

Tests block sockets and mock the real SDK HTTP transport. Gemini cases include both stages, both languages, all five developmental bands, schema errors, refusals, rate limits, timeouts, cancellation, usage/cache/thought reconciliation, unknown costs, stage budgets, quality rewriting, sanitized failures, API injection and lifespan cleanup. Dummy strings are used instead of real credentials. SDK finalizers are collected and drained while the guarded test loop is running; both pools are also explicitly closed.

## Proposed live smoke test — approval required, not executed

Proposed model for **both stages: `gemini-3.5-flash-lite`**. As checked on **2026-11-02**, Google lists it as stable, supporting structured outputs, with 1,048,576 input capacity and 65,536 output capacity. This is a low-cost capability-based selection, not a validated story-quality recommendation. [Official model specification](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite).

The synthetic [newborn request](examples/gemini-smoke-request.en.json) asks for four short sensory pages, 5–15 words each, adult read-aloud, with no conflict requirement or inferred pronouns. [Proposed runtime configuration](examples/gemini-smoke-runtime.json) sets 8,000 input tokens per attempt, 800 output tokens per stage (including thinking), three attempts, 26,400 aggregate reservation units, 30 seconds/attempt, 90 seconds overall and a **USD 0.015 request ceiling**. These small caps can cause incomplete JSON or a quality failure; successful generation is not guaranteed. A failure requires review, not an automatic increase of limits.

Published standard text prices at review: **USD 0.30 per million input tokens and USD 2.50 per million output tokens**, including thinking. The configuration uses these paid rates even if the account might qualify for free use. Normal two-call worst-case estimate: **USD 0.0088**; three-call worst-case estimate: **USD 0.0132** under the configured caps. Actual use is unknown before a live response; these are conservative planning estimates, not exact charges. Google lists free-tier input/output for this model, but account/project eligibility, regional availability and remaining quota have not been checked. A key alone does not establish free eligibility. [Official pricing and tier table](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite).

No billing activation or Cloud changes are required by this procedure, and none will be performed automatically. Before approval, confirm the account can access this model and review the current tier/quotas in AI Studio yourself. Free-tier content may be used to improve Google's products; paid-tier handling differs. Use synthetic data only and review the applicable [Gemini API terms](https://ai.google.dev/gemini-api/terms). Do not enable SDK/HTTP debug logs or external tracing. Local service authentication and aggregate cross-request spend controls remain outside this milestone.

**Do not run the following live procedure until explicitly approved.** It sends the synthetic brief to Google and can incur charges. Arrange `GEMINI_API_KEY` locally through your existing secret-management method; never paste it into chat, commit it, echo it or place it in shell history. The key may be stored in the Git-ignored local `.env` file. Uvicorn loads it only when explicitly passed `--env-file .env`; it preserves existing process variables. The command below clears a stale process key so the file supplies it. Required environment configuration:

```powershell
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
$env:STORYFORGE_CONFIG = (Resolve-Path .\docs\examples\gemini-smoke-runtime.json).Path
$env:STORYFORGE_ALLOW_PAID_CALLS = 'true'
.\.venv\Scripts\python.exe -m uvicorn storyforge.api.configured:create_configured_app --factory --env-file .env --workers 1 --host 127.0.0.1 --port 8000 --no-access-log
```

The server starts without Gemini calls. In a second shell at the repository root, run this **single POST**, only after approval:

```powershell
$smokeBody = Get-Content -Raw -Encoding UTF8 .\docs\examples\gemini-smoke-request.en.json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/v1/stories/generate' -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($smokeBody))
```

That POST runs Input Validation → Planner → Writer → Quality Gate through `StoryEngine.generate`, with bounded recovery. It is not a direct adapter call. Repeating the POST starts another independently budgeted request; do not retry manually without considering cumulative spend. `/health` alone never verifies credentials or model availability.

After Ctrl+C stops the server, clear the process-local variables:

```powershell
Remove-Item Env:STORYFORGE_ALLOW_PAID_CALLS -ErrorAction SilentlyContinue
Remove-Item Env:STORYFORGE_CONFIG -ErrorAction SilentlyContinue
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
```

## Languages and remaining limits

Gemini receives Unicode input and language-aware profile/prompt snapshots without translation or script conversion. No new language restriction is introduced. Current executable contracts remain Hebrew/English; neither provider coverage nor JSON success establishes fluency in any language. Before adding another language, native reviewers must assess pronouns/agreement, adult read-aloud quality and all developmental bands; registry, segmentation and script checks need the changes already proposed in [EXTENSIBILITY.md](EXTENSIBILITY.md). No-space scripts cannot inherit current whitespace word targets blindly. Token reservations depend on UTF-8 byte length and will vary across scripts; use measured per-language usage later to tune caps without weakening quality.

Open: approved live-run/model availability and tier, real literary quality, framing estimate calibration, language-specific reviewer thresholds, provider comparison/fallback policy, privacy/release requirements and future languages. Stop after Milestone 6; no Milestone 7 work is authorized.

## Local preflight follow-up

The explicit `.env` path and current smoke files were verified without starting a server, constructing an SDK client or making any provider request. The real local key was read only in a disposable process and never displayed; its value is excluded from secret repr/serialization. See [preflight report and commands](GEMINI_PREFLIGHT.md). Loading a secret is not authentication or project-access verification. No limits were changed.
