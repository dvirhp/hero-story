# Safe provider diagnostics

Approved Milestone 6 diagnostic-only follow-up. No live request is authorized by
this patch, and Milestone 7 remains out of scope.

Every failed `usage.attempts` entry now includes `provider_diagnostic`:

```json
{
  "category": "rate_or_quota_limit",
  "upstream_http_status": 429
}
```

This is an illustrative offline example, not recovered evidence from Roy's
previous live failure. Successful attempts have null diagnostics. A failed
attempt remains in the ledger if a later retry succeeds.

`ProviderDiagnostic` is SDK-independent, immutable, strictly typed and rejects
extra fields. Categories are a fixed enum; status is a strict integer from
100 through 599 or null. No exception strings, raw responses, prompts, URLs,
headers, credentials, arbitrary provider messages or stack traces are copied.
There are no new logging calls or content stores.

## Categories and propagation

Gemini HTTP failures preserve the upstream status and these categories:

| Status | Category |
| --- | --- |
| 400 | `invalid_request` |
| 401 | `authentication` |
| 403 | `permission_denied` |
| 404 | `not_found` |
| 408 / 504 | `timeout` |
| 409 | `conflict` |
| 429 | `rate_or_quota_limit` |
| Other 5xx | `server_error` |
| Other recognized HTTP status | `configuration_error` |

Transport categories distinguish `connection_error`, `dns_error`, `tls_error`,
`transport_error` and `timeout`. DNS/TLS detection examines only known exception
types in a bounded explicit cause chain, never their text. Missing evidence
remains generic. A 429 does not establish whether a short rate limit or persistent
quota exhaustion caused it; a 404 does not establish which resource was absent.

Local configuration/output/refusal/safety/cancellation failures have fixed
categories and nullable status. Older or other adapters that supply no detailed
diagnostic receive a coarse category derived from their existing error code,
or `unknown`; upstream HTTP status is never invented. This patch adds detailed
HTTP/transport extraction to Gemini and leaves OpenAI execution unchanged.

Flow: Gemini `ProviderFailure.provider_diagnostic` -> engine attempt completion ->
`AttemptRecord.provider_diagnostic` -> `UsageSummary` -> saved JSON/HTTP response.
The engine still reconstructs safe public errors; it now retains typed diagnostic
metadata separately. Unknown tokens/cost retain their existing reservations.

## Stop reason and compatibility

`GenerationFailure.stop_reason` separately records why orchestration stopped:
`attempt_capacity_exhausted`, `token_budget_exhausted`, `cost_budget_exhausted`,
`input_capacity_exceeded`, generic `resource_capacity_exhausted`,
`deadline_exceeded`, `cancelled`, `provider_failure`, `configuration_error`,
`quality_rejected` or `input_rejected`.

For example, two failed Planner attempts may retain `server_error`/503 in each
attempt while the final public code stays `BUDGET_EXCEEDED` and the stop reason is
`attempt_capacity_exhausted`. The engine still reserves a Writer slot; it does not
spend a third Planner attempt when a fourth call would then be needed to write.

V1 and v2 public error codes and HTTP mappings are unchanged. These are additive
metadata fields; clients that reject unknown response fields need to accept the
new fields. Older stored JSON remains parseable: missing upstream status stays
null, coarse categories may derive from existing codes, and missing historical
stop reasons remain null. No old live artifact is rewritten or retroactively
assigned an upstream status.

Retry classification is unchanged, including its coarse treatment of 429,
transport errors and most 5xx responses. Diagnostics do not decide whether to
retry. No limits, tariffs, model settings, deadlines or provider SDK retries were
changed. Request-local cancellation cleanup preserves the safe attempt ledger.

## Diagnosing a future explicitly approved run

1. Obtain separate approval for exactly one end-to-end POST, the exact v2 request
   and isolated runtime. Preserve three attempts, one rewrite, 45/135-second
   deadlines and the $0.075 ceiling. Do not rerun the old live helper automatically.
2. Start the configured local server with explicit `.env` loading, one worker,
   tracing disabled and access logging disabled. Do not enable SDK/HTTP debug or
   wire logging. Credentials stay outside artifacts and command arguments.
3. Send one POST with client retries and redirect following disabled. Save the
   application JSON response, HTTP status and elapsed time in an ignored local
   location. Do not capture headers, raw upstream bodies or exception strings.
4. Read `usage.attempts[*].provider_diagnostic`, each existing `error.code`, and
   final `stop_reason`. Report unknown status/usage/cost explicitly. Do not claim
   that StoryForge's HTTP 503 was Google's status unless the new field establishes it.
5. Stop the server and restore temporary environment variables in a finally block.
   Stop after failure or timeout; another POST requires new explicit approval.

The previous failure's precise root cause remains unknown. This patch improves
the next observation; it does not authorize a new observation or guarantee a
complete diagnosis from a coarse status/category.

Offline tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_provider_diagnostics.py tests/test_gemini_provider.py tests/test_gemini_integration.py tests/test_engine.py tests/test_api.py tests/test_real_accounting.py -q
```

Verification: full Python 3.13.3 suite **792 passed, 0 failed** (215.79 seconds),
preserving all original 750 cases and adding 42 diagnostic cases. Python 3.12.16
diagnostic/engine/API/Gemini integration subset: **189 passed, 0 failed** (52.60
seconds). Wheel/source builds passed. Tests use dummy credentials and mocked
transports with sockets blocked; no local live artifacts are read by the tests.
No live request, credential read, billing change, push or deployment occurred.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.tools\Scripts\uv.exe run --python 3.12 --isolated --locked python -m pytest tests/test_provider_diagnostics.py tests/test_engine.py tests/test_api.py tests/test_gemini_integration.py -q
.\.tools\Scripts\uv.exe build
```
