# Gemini smoke-test preflight — 2026-11-02

Ready for an explicitly approved first live request. No Gemini API request has been made. This is a Milestone 6 configuration follow-up, not Milestone 7.

- The local `.env` exists and is ignored by Git. Its nonempty `GEMINI_API_KEY` loads through Uvicorn's explicit `--env-file .env` path and is accepted by the application's secret configuration contract. The real value was never displayed, logged or serialized. Verification ran in a disposable process with network sockets blocked and live execution disabled; no SDK client/server/generation was started. This does not verify authentication.
- The missing loader dependency was added: `python-dotenv>=1,<2`, locked to 1.2.4. No application, domain, orchestration or budget code changed. Default startup still does not discover `.env`. Existing process variables take precedence over file values; the command below removes a stale process key first.
- Exact configured model for both stages: **`gemini-3.5-flash-lite`**. Google currently lists it as stable, supporting structured outputs. Availability for this particular key/project, regional eligibility and remaining quotas cannot be verified without authorized API access. [Official model specification](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite).
- Runtime JSON, synthetic English newborn request, profile normalization and engine capacity/pricing configuration all validate. The offline mock smoke test runs the same files through the entire engine and accepts four short read-aloud pages.
- Limits are unchanged: **3 total provider attempts**, at most **1 rewrite**, **USD 0.015** request budget, **26,400** aggregate reserved token units, **8,000** input and **800** output tokens per attempt, including thinking; 30 seconds/attempt and 90 overall. These are estimated-cost guards, not guaranteed invoice caps.
- Current configured standard-text rates match Google's public table: USD 0.30/million input and USD 2.50/million output. The configured worst-case estimates are USD 0.0088 for two calls and USD 0.0132 for three. Google lists a free tier, but account eligibility has not been checked and no free-use assumption is made. [Official pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite).

Offline verification: **544 passed, 0 failed** in the complete Python 3.12.16 suite, including the unchanged original 541 tests. Python 3.13.3 targeted dotenv/configuration and mock pipeline checks: **4 passed**. New tests cover explicit loading/redaction, absence of implicit discovery, and process-variable precedence. All use dummy keys and blocked sockets; the actual local credential was checked separately without generation. Source/wheel builds passed, and the four targeted loader/mock-pipeline checks also passed against the installed wheel on Python 3.12.16.

## Commands after explicit approval only

Run from the repository root. Synchronization installs the newly locked loader dependency:

```powershell
.\.tools\Scripts\uv.exe sync --locked
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
$env:STORYFORGE_CONFIG = (Resolve-Path .\docs\examples\gemini-smoke-runtime.json).Path
$env:STORYFORGE_ALLOW_PAID_CALLS = 'true'
.\.venv\Scripts\python.exe -m uvicorn storyforge.api.configured:create_configured_app --factory --env-file .env --workers 1 --host 127.0.0.1 --port 8000 --no-access-log
```

The startup command loads the key but makes no provider call. In a second PowerShell window at the repository root, this single POST is the **first live test**. Do not execute it before approval; it can incur charges and sends the synthetic brief to Google:

```powershell
$smokeBody = Get-Content -Raw -Encoding UTF8 .\docs\examples\gemini-smoke-request.en.json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/v1/stories/generate' -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($smokeBody))
```

Do not repeat the POST automatically: each request has a separate budget. After Ctrl+C stops the server, clear process-local switches:

```powershell
Remove-Item Env:STORYFORGE_ALLOW_PAID_CALLS -ErrorAction SilentlyContinue
Remove-Item Env:STORYFORGE_CONFIG -ErrorAction SilentlyContinue
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
```

The `.env` file remains local and ignored. No billing settings, model/token/budget limits, remote repositories or deployments were changed. No live call or Milestone 7 work was performed. Approval remains pending.
