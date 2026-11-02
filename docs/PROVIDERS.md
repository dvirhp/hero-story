# Providers and explicit OpenAI configuration

Milestone 5 adds the official async OpenAI SDK adapter. Default `create_app`, demo and tests remain fake, independent of environment credentials. Importing modules makes no calls. No live call was made during implementation. Domain schemas and provider protocol remain SDK-independent; [future provider/language work](EXTENSIBILITY.md) requires separate approval.

## Composition and settings

`AppSettings.provider` accepts `fake` or `openai`. `model` is the common fallback; optional `planner_model` and `writer_model` override it. Each real stage must resolve to an explicit model ID. Fake stages retain `scripted-v1`. HTTP requests cannot select providers or models.

`ModelCapabilities` declares model/version, context capacity, output capacity, positive framing/schema overhead and structured-output support. `ModelPricing` declares provider/model/version, positive input/output reservation rates and optional actual input/output/cached rates. No real model ID, price or capacity default is supplied. `RuntimeConfiguration` binds settings, aggregate limits and each stage's declarations. Direct dependency injection through `Resources` is also supported. `OpenAIConfig` requires an explicit secret and timeout; the secret is excluded from repr/serialization and never enters graph state.

Default limits remain three total attempts, one rewrite, 30 seconds/attempt, 90 overall, 8,000 input, 1,200 planner output, 3,000 writer output and 33,000 aggregate reserved tokens. Settings can explicitly change capacities/time limits subject to validation. Real mode requires a positive aggregate USD ceiling and matching stage metadata. Verify context/output capacity and strict Responses schema support for every chosen model before any live run. A capability declaration is not a network-verified guarantee.

The optional `storyforge.api.configured:create_configured_app` factory reads these variables during lifespan only:

| Variable | Requirement |
| --- | --- |
| `STORYFORGE_ALLOW_PAID_CALLS` | Exactly `true`; checked before credential access |
| `STORYFORGE_CONFIG` | Explicit path to validated runtime JSON |
| `OPENAI_API_KEY` | Explicit nonempty secret; never needed for fake/tests |

There is no `.env` auto-loading or key discovery. [.env.example](../.env.example) is documentation only. The normal fake factory ignores all three variables. The configured factory validates capacities at startup, constructs one async client pool without probes, and closes it on shutdown. Startup health never calls OpenAI. The adapter fixes the official API base URL, disables proxy environment discovery/default redirects and sets SDK retries to zero. Custom transport injection is available for offline tests; arbitrary production endpoints are not exposed by this milestone.

## Structured responses and failures

Distinct existing versioned Planner/Writer prompts are reused. `structured_schema` projects Pydantic schemas to strict JSON schema: every property required, nullable optional values, forbidden extra properties. Constraints unsuitable for remote strict schema are removed only from the projection; full local Pydantic validation and context/profile/quality checks remain mandatory. This does not certify compatibility with every OpenAI model, especially fine-tuned models.

Responses use `store=False`, `background=False`, `stream=False`, `tools=[]`, a bounded output cap and the smaller remaining/configured timeout. Reasoning content is ignored. Cached/reasoning token counts are subsets of input/output counts and never added twice. Provider refusal/content filtering is terminal. Incomplete, malformed and schema-invalid output can recover through existing graph edges. Unsafe output takes terminal precedence even when malformed. No failed draft or raw provider diagnostic enters a public result.

Timeout/408 are retryable deadlines; connection errors, 409/429/5xx are retryable availability failures. Numeric/date Retry-After is normalized, waited within the overall deadline and never creates extra attempt slots. Other 4xx, including authentication and unsupported configuration, are terminal configuration failures. Cancellation propagates from adapter to the existing journal-aware wrapper. Cancellation cannot guarantee a remotely accepted request is unbilled. See [API status mapping](API.md); exhausting retry slots may yield `BUDGET_EXCEEDED` with the original failure in the ledger.

## Reservations and cost limits

Each attempt reserves instructions, JSON input and projected schema as UTF-8 bytes plus configured framing overhead, then the entire output cap. This is a conservative engineering estimate for the selected model's ordinary byte-based tokenization, not exact tokenizer usage or a universal provider guarantee. Verify adequate framing overhead/model tokenization before paid use; provider-side transformations or an incorrect declaration can exceed the estimate. No tokenizer downloads occur. Reported overages terminate further execution and remain in the ledger.

Before a planner call, remaining capacity must also cover the writer's worst-case input/output and its own tariff. All reservations remain held; retries and rewriting share the same three slots. Positive reservation prices must cover supplied actual rates. Unknown actual prices are allowed only with explicit reservation ceilings; they do not mean free service.

SDK usage, when complete/valid, is `reported`; missing/inconsistent usage is `unknown` with null counts, not zero or invented estimates. `has_unknown_cost` is independent of `has_unknown_usage`: known token counts with missing rates still have unknown cost. Known cost is only a subtotal. Cached tokens use their configured rate, falling back conservatively to the standard input rate; missing cache detail also uses the standard rate. Reasoning tokens remain within charged output totals. `upper_estimated_cost_usd` is the held configured estimate, not a guaranteed invoice cap. Prices can change, requests can be billed after cancellation and non-token charges/discounts are outside this estimator. Verify current rates before explicitly approving a paid run.

## Exact PowerShell commands

Safe setup and verification, from the repository root:

```powershell
py -m venv .tools
.\.tools\Scripts\python.exe -m pip install uv==0.13.6
.\.tools\Scripts\uv.exe sync --locked
.\.venv\Scripts\python.exe -m pytest -q
.\.tools\Scripts\uv.exe run --python 3.12 --isolated --locked python -m pytest -q
.\.tools\Scripts\uv.exe build
.\.venv\Scripts\python.exe -m uvicorn storyforge.api.app:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

Optional live smoke procedure below is **documentation only, not executed or authorized**. It can incur charges and sends child/story data to OpenAI. Obtain separate approval and use synthetic inputs. Copy [the intentionally invalid template](examples/openai-runtime.template.json) to an ignored `.env.runtime.json`, replace model IDs and all required null values with reviewed capacities, overhead, positive reservation prices and an approved USD ceiling. Actual rate nulls retain explicitly unknown cost. You may use distinct models and tariffs for the two stages. No real model/pricing recommendation is implied.

Only after approval and externally arranging a process-local `OPENAI_API_KEY` through your secret-management method (never commit it or paste it into a command history):

```powershell
$env:STORYFORGE_CONFIG = (Resolve-Path .\.env.runtime.json).Path
$env:STORYFORGE_ALLOW_PAID_CALLS = 'true'
.\.venv\Scripts\python.exe -m uvicorn storyforge.api.configured:create_configured_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

In a second shell, the following POST is the optional **paid** smoke call; health alone is not a provider test:

```powershell
$smokeBody = Get-Content -Raw -Encoding UTF8 .\docs\examples\story-request.en.json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/v1/stories/generate' -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($smokeBody))
```

Stop the server with Ctrl+C; remove process variables when finished:

```powershell
Remove-Item Env:STORYFORGE_ALLOW_PAID_CALLS -ErrorAction SilentlyContinue
Remove-Item Env:STORYFORGE_CONFIG -ErrorAction SilentlyContinue
Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
```

Do not enable SDK/HTTP debug logging, body logging or external tracing for child data. `store=False` is not a complete provider-retention guarantee. This unauthenticated local application is not approved for public deployment. Cross-request spend, auth, privacy obligations and human quality evaluation remain separate decisions.

Implementation references: official [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses), [Python SDK](https://developers.openai.com/api/reference/python), and [Responses create](https://developers.openai.com/api/reference/python/resources/responses/methods/create). Dependency versions are recorded in `uv.lock`; no live capability or pricing probe is performed.
