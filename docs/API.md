# Local FastAPI application (Milestone 4)

> Approved page-count update: new work uses [explicit-length v2](PAGE_COUNT_V2.md). The user supplies page_count; age controls developmental guidance and page density. Deprecated v1 keeps its original behavior. Historical milestone sections below describe v1 unless labeled v2. No live calls were made in this follow-up; Milestone 7 remains unapproved.


Milestone 4 wraps the existing bounded engine. Default output is **synthetic fixture text**, not creative AI-generated literature. The default factory needs no API key. Milestone 5 adds a separate explicitly configured OpenAI factory; database, hosting and authentication remain out of scope.

## Application and contracts

`storyforge.api.app:create_app` is a factory, with no module-level application or provider calls. Lifespan loads validated default developmental configuration into immutable `Resources`, or accepts explicitly injected resources. Startup configuration failures stop startup. Shutdown releases the resource reference. No HTTP client pool or external service is created.

`get_resources`, `get_provider` and `get_engine` are async dependencies. Each generation gets a fresh local provider and engine; only immutable non-personal configuration is shared. Override dependencies through `app.dependency_overrides`, or pass `create_app(resources=Resources(...))` for deterministic settings, profiles, budgets, pricing, quality rules and clocks. Tests can supply the existing scripted `FakeProvider` directly. No provider/model is selected from HTTP input.

| Endpoint | Request | Response |
| --- | --- | --- |
| `GET /health` | None | HTTP 200, `{"status":"ok"}`; process health only, no engine/provider probe |
| `POST /v1/stories/generate` | Existing strict `StoryRequest` JSON object | HTTP 200 with existing `GenerationSuccess`, or typed `GenerationFailure` with mapped status |
| `GET /docs` | None | FastAPI's interactive OpenAPI documentation |
| `GET /openapi.json` | None | Actual request/success/error schemas |

The route preserves the pre-existing `/v1/stories/generate` plan; no `/api` prefix or route alias is added. Reuse the domain models; the only new response DTO is the small HTTP health response. FastAPI's parsed JSON objects re-enter the existing model's JSON validation mode using a boundary-only `BeforeValidator`: `interests` arrays become immutable tuples while strict integer ages, forbidden extra fields and other domain constraints are preserved. No coercion of years, numeric strings, floats or booleans into `age_months` is allowed. Newborn age zero is valid; there is no arbitrary maximum.

The response includes an approved story, quality observations, provider-attempt usage/cost estimates and engine latency. Failure bodies never contain a draft, plan, raw response, prompts, validation inputs or stack trace. `total_latency_seconds` is engine time, not total HTTP parsing/setup time; pre-engine validation failures use zero latency and an empty attempt ledger. Only success has a `story` field.

Generation, health and error responses carry a new server-generated UUID in `X-Request-ID`; generation/error bodies use the same ID. Incoming IDs are not echoed. `Cache-Control: no-store` prevents ordinary response caching. This is not a retention or client-security guarantee. Built-in documentation/schema responses are not personalized and do not use the generation request-ID wrapper.

## HTTP errors

All failures reuse `GenerationFailure` and `GenerationError`. Error messages are fixed and bounded, and default Pydantic/FastAPI validation details are not exposed. `SafeRoute` catches dependency, endpoint and response-validation exceptions inside the routing boundary so the server does not re-raise those private exceptions into its error logger. No body/content logging or telemetry is added.

| Code / condition | HTTP | Meaning |
| --- | --- | --- |
| `INPUT_INVALID` | 422 | Malformed JSON, missing/extra fields, unsupported values, wrong body/media shape, or input controls |
| `POLICY_REJECTED`, validation stage | 400 | Narrow deterministic input-policy rejection before provider calls |
| `POLICY_REJECTED`, provider/output stage | 502 | Unsafe provider output; not blamed on the caller |
| `QUALITY_REJECTED` | 422 | Generated draft failed quality; the request may be entirely valid |
| `PROVIDER_OUTPUT_INVALID` | 502 | Non-recoverable provider schema/context failure |
| `PROVIDER_REFUSED` | 502 | Provider refused; no inference that the user request was invalid |
| `PROVIDER_UNAVAILABLE` | 503 | Non-recoverable transport/provider availability failure |
| `BUDGET_EXCEEDED` | 503 | Attempts, token reservations or cost capacity cannot support further work |
| `DEADLINE_EXCEEDED` | 504 | Overall generation deadline expired |
| `CONFIGURATION_ERROR` | 500 | Unexpected internal/dependency/result-validation failure |
| `CANCELLED` | 499 | Best-effort diagnostic response on cancellation/disconnect; 499 is non-standard |
| Missing route / wrong method | 404 / 405 | Same failure envelope with `INPUT_INVALID`; preserve `Allow` on 405 |

Keep the documented `422 QUALITY_REJECTED` behavior for compatibility. It does **not** mean schema-invalid input: inspect `error.code` and `error.stage`. The plan's general `400 policy rejection` is clarified by stage so provider-produced unsafe content receives 502. A transient provider/schema failure that exhausts the shared engine budget is returned as `503 BUDGET_EXCEEDED`, with the original safe stage failure in the attempt ledger. An attempt timeout that spends the last available recovery capacity can likewise end as budget exhaustion; an overall deadline is 504. Transport-level body parsing errors emitted as HTTP exceptions retain their status (for example, invalid body encoding can be 400).

Sanitized validation-error example (IDs vary):

```json
{
  "request_id": "00000000-0000-4000-8000-000000000001",
  "usage": {
    "attempts": [],
    "known_estimated_cost_usd": 0.0,
    "upper_estimated_cost_usd": 0.0,
    "has_unknown_usage": false,
    "has_unknown_cost": false
  },
  "total_latency_seconds": 0.0,
  "status": "failure",
  "error": {
    "code": "INPUT_INVALID",
    "stage": "validation",
    "retryable": false,
    "message": "Request does not match the supported input contract"
  },
  "quality": null
}
```

Selected success fields below are a projection, not the full response schema. The actual response additionally contains ordered approved pages, full quality observations, attempts and timing:

```json
{
  "status": "success",
  "request_id": "00000000-0000-4000-8000-000000000002",
  "story": {
    "language": "he",
    "direction": "rtl",
    "profile_id": "newborn",
    "profile_version": "development-v1"
  },
  "quality": {"passed": true},
  "usage": {"has_unknown_usage": true}
}
```

## Fake-only local behavior

`LocalFixtureProvider` reads the already normalized brief in the engine's structured provider request and delegates each stage to one existing `FakeProvider` invocation. Fixture construction was extracted from the Milestone 3 demo into `llm/fixtures.py` and is shared, not duplicated in API routes. It does not implement planning/writing agents, infer pronouns, satisfy creative guidance semantically, or retry. Text deliberately repeats simple words and supplied names. All orchestration, normalization, quality checking and accounting stay in their existing modules.

Defaults retain unknown token usage, conservative synthetic reservations, a zero fake tariff and the existing three-attempt/one-rewrite limits. HTTP adds no retries, idempotency, queue, timeout policy or background work. Repeating a POST is a new generation. Accepted fixture text only demonstrates limited deterministic checks, not literary quality, fluency, developmental suitability or complete safety.

## Cancellation and disconnects

The endpoint awaits the existing async engine. After FastAPI consumes the body, two **request-scoped** tasks race engine completion and an ASGI `http.disconnect` receive event. On observed disconnect, cancel and await generation, retain its available safe ledger, and emit a best-effort 499 failure instead of a story. The disconnected client usually cannot receive that response. On server/request task cancellation, drain both tasks and propagate cancellation to the ASGI server. No tasks are scheduled through background jobs or left running intentionally after the request.

There is no competing body reader or polling loop, and no blocking I/O in the generation route. Lifespan reads the small packaged config before serving requests. The engine's existing timeout handles generation; the API does not introduce a separate retry or budget loop. In-process tests simulate disconnect and server cancellation to verify cooperative provider termination.

Limits: detection depends on the ASGI server/transport delivering disconnect events; a disconnect may be observed after work completes, and network/server failure can delay or prevent detection. Cancellation is cooperative; non-cooperative injected providers, forced process shutdown or future remote requests cannot be guaranteed stopped/unbilled. This is no distributed cancellation mechanism. Body-read/connection establishment behavior belongs to the ASGI server. No paid remote provider exists here.

## Windows PowerShell usage

From the repository root:

```powershell
py -m venv .tools
.\.tools\Scripts\python.exe -m pip install uv==0.13.6
.\.tools\Scripts\uv.exe sync --locked
.\.venv\Scripts\python.exe -m uvicorn storyforge.api.app:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

The server runs in the foreground; Ctrl+C stops it. Access logging is disabled so URLs/query strings are not logged by that command. No API keys or `.env` file are needed. In a second PowerShell window at the repository root:

```powershell
Start-Process 'http://127.0.0.1:8000/docs'
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health'

$heBody = Get-Content -Raw -Encoding UTF8 .\docs\examples\story-request.he.json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/v1/stories/generate' -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($heBody))

$enBody = Get-Content -Raw -Encoding UTF8 .\docs\examples\story-request.en.json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/v1/stories/generate' -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($enBody))
```

The [Hebrew newborn JSON](examples/story-request.he.json) and [English older-child JSON](examples/story-request.en.json) contain synthetic names and explicit language-specific pronouns. UTF-8 bytes avoid PowerShell 5.1 encoding ambiguity. Swagger UI normally loads assets from a public CDN; its browser UI may need internet. `/openapi.json`, API calls and tests need no external service after dependency installation. No offline UI assets or frontend are introduced.

Run verification without a server:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.tools\Scripts\uv.exe run --python 3.12 --isolated --locked python -m pytest -q
.\.tools\Scripts\uv.exe build
```

HTTP tests use HTTPX `ASGITransport`, explicit lifespan contexts and the existing guarded event loop. They never open a TCP listener or call an external provider. This follows FastAPI's [async testing](https://fastapi.tiangolo.com/advanced/async-tests/) and [dependency override](https://fastapi.tiangolo.com/advanced/testing-dependencies/) interfaces. Local application tests do not fetch Swagger CDN assets.

## Git and remaining work

Branch: `feature/milestone-4-fastapi`, created from the clean completed Milestone 3 branch. Preserve history and make small tested commits after checking staged changes. Do not commit secrets, caches or generated builds; existing ignores remain in effect. No remote, merge, push or deployment was performed or authorized.

Open: verified model/tokenization/pricing metadata, separately approved paid evaluation, multilingual/provider expansion, human quality thresholds, production authentication/abuse controls and privacy/release decisions. OpenAI and Gemini integrations are implemented and tested offline. This local unauthenticated application is not a public deployment plan. Stop after Milestone 6.
