# StoryForge AI independent QA handoff

Date: 2026-11-05 (Asia/Jerusalem). Branch: `feature/storyforge-qa-foundation`.
Worktree: `C:\Users\dvir3\storyforge-qa`.
Repository: `C:\Users\dvir3\OneDrive\Desktop\heroStory`.
Baseline: `5ae24e9c14dee82a1aca3e6eda45dff88fe4aebc`, identical to
`feature/milestone-6-page-count-v2` at inspection. Agent 1's working branch has
uncommitted diagnostics changes, deliberately excluded. No production files,
shared configuration, frontend or persistence code were modified. No merge,
push, deployment or live AI request was performed.

Implementation commit: `136296c83f46cd8305b0580b6a29a9598a96f5a2`.
Find it again using `git log -1 --format=%H -- tests/test_qa_v2_http.py`.
The final documentation commit is `git rev-parse HEAD`; a commit cannot contain
its own hash. These commands identify commits without conversation context.

## Architecture and reproducible commands

The committed project is Python 3.12+, FastAPI, Pydantic v2 and LangGraph. The
existing suite uses pytest, pytest-socket and HTTPX. `pyproject.toml` defaults to
`--disable-socket`; the existing session event loop is constructed first because
Windows asyncio needs a local socket pair. Test execution blocks sockets.
The baseline has no frontend, database or browser dependency manifest.

New `tests/test_qa_v2_http.py` exercises the actual FastAPI factory, lifespan,
v2 route, JSON contract, dependency injection, normalization, LangGraph execution,
quality gate, request ID middleware and usage/budget ledger. Only the provider
is scripted using actual FakeProvider/FakeStep. HTTPX ASGITransport runs locally
in-process, with no TCP server. Fixtures in `tests/fixtures/qa_v2_requests.json`
are synthetic deterministic briefs across five age bands and both implemented
languages. Existing Roy fixture covers the complete 27-page Hebrew alphabet.
Generated filler is constructed through the production fixture helper, so this
is not an independent oracle for prompt meaning or language quality.

From the QA worktree in PowerShell, using the existing installed environment:

```powershell
$env:PYTHONPATH = 'C:/Users/dvir3/storyforge-qa/src'
& C:/Users/dvir3/OneDrive/Desktop/heroStory/.venv/Scripts/python.exe -m pytest -q
& C:/Users/dvir3/OneDrive/Desktop/heroStory/.venv/Scripts/python.exe -m pytest tests/test_qa_v2_http.py -q
```

PYTHONPATH ensures the isolated source is tested rather than the other branch's
editable install. Only the interpreter/dependencies are reused, without modifying
that environment. To reproduce on a new machine, provision the locked dev
dependencies in an isolated environment first (`uv sync --locked`); dependency
installation may require network, but tests require no keys or paid calls.
Do not load `.env`, run live demos or use configured real-provider factories.

## Risk-based coverage and priorities

| Priority / risk | Automated evidence | Limit / next integration |
| --- | --- | --- |
| P0 wrong book length | New HTTP tests hold seven pages across 10 month boundary/open-ended ages; existing v2 matrix crosses 1/6/27/32 pages, both languages and profiles | UI age changes must preserve explicit count |
| P0 child-data or credential exposure | New canary provider-error sanitation, malformed-field sanitation, no child names in captured logs/stdout/stderr, no failed draft/plan in failures, no-store, server UUID replacing client ID | No repository-wide secret certification, retention audit or production logging test |
| P0 unbounded paid retries | New HTTP checks exact invocation/ledger counts for failures and rewrite; existing shared-budget, admission, reservation, cancellation and timeout tests | No paid transport or remote billing guarantee |
| P0 unsafe/rejected draft published | New terminal unsafe output, exhausted malformed output, incomplete/reordered education, repeated quality failure return no story | Literal moderation has known semantic gaps |
| P1 strict input | New invalid page types/counts, missing count, boolean age, unsupported language, bidi override and private extra fields make zero provider calls | Existing API tests add malformed JSON/media and disconnects |
| P1 RTL/Unicode corruption | New exact Hebrew niqqud and multiword names, accented Latin, emoji themes, direction and target order | No DOM/CSS, mixed-direction layout, PDF or print verification |
| P1 ordered education | New HTTP target sequence and rejected reorder; existing Roy 27 targets/final forms and generic targets | Literal inclusion cannot establish accurate teaching |
| P1 age suitability | Existing profile boundaries/configuration/density; new fixed-count boundary HTTP tests | Human review required; profiles are hypotheses |
| P1 provider integration | Existing OpenAI/Gemini adapter/engine suites use mocked transports and dummy credentials | Agent 1 changes not present; no live provider compatibility claims |
| P1 reading/save/export | None in baseline | Depends on Agent 2, Agent 3 and future export implementation |
| P2 literary variety | Existing advisory repetition checks only | Separate human rubric in QA_HUMAN_REVIEW.md |

Current executable languages are Hebrew and English. Accents/emoji/niqqud
coverage is Unicode preservation, not support for additional story languages.
No line/branch coverage tool was run; scenario coverage above is the actual
coverage claim, not a percentage or full E2E claim.

## Failure scenarios and privacy boundaries

New tests assert refusal -> 502, unavailable -> 503, terminal unsafe output ->
502, exhausted malformed output/attempt timeouts -> 503 BUDGET_EXCEEDED, and
unrepaired quality failure -> 422 QUALITY_REJECTED. Planner recovery stops at
two calls when no slot remains for mandatory writing; quality rewrite consumes
the third shared attempt. Fake latency simulates attempt timeouts without sleeping.
Existing engine tests separately cover actual asynchronous timeout and overall
deadline handling. No new timeout test claims real network cancellation.

Privacy assertions use dummy canaries, never actual credentials or child data.
They observe application test logs and captured output, not external ASGI server,
proxy, browser telemetry, persistent store or deployed infrastructure. The local
API is unauthenticated by design and is not a public-release security approval.
Stored story access control, tenant isolation, deletion/retention and secure
exports remain future integration tests.

## Browser and persistence blockers

`qa/e2e/` contains optional, unexecuted Playwright configuration and a minimal
local smoke spec. It changes no package manifests and starts no server. See its
README for integration prerequisites. No runnable frontend exists in this
baseline; Agent 2's separate worktree is not imported or modified. Browser
journey selectors and accessibility contracts must follow its reviewed UI.
The smoke only tests a responsive local page, not generation. External page
requests and content artifacts are disabled; the server must separately use fake.

Agent 3's database work is likewise absent. No real PostgreSQL, migration,
transaction, saved-book, ownership or restart-persistence tests were run.
Integrate independently reviewed branches before enabling these tests. Rerun
the complete offline suite after Agent 1's diagnostics changes are integrated;
error shape/redaction and retry counts are particular compatibility risks.

## Results and confirmed defects

Verification on Windows, Python 3.13.3, with sockets disabled:

| Run | Passed | Failed | Skipped | Notes |
| --- | --- | --- | --- | --- |
| Complete suite at initial QA collection | 784 | 0 | 0 | 166.43 seconds; 750 baseline + first 34 QA cases |
| Final focused QA suite | 37 | 0 | 0 | 4.03 seconds; includes three cases added after full-suite collection |
| Final collection-only | 787 collected | n/a | n/a | Confirms 750 baseline + 37 QA cases |
| Playwright | Not executed | n/a | n/a | Missing frontend and browser tooling, not counted as pytest skips |
| PostgreSQL integration | Not available | n/a | n/a | Persistence not in baseline |

All 787 distinct final pytest cases were exercised successfully across the full
and focused runs; a single final 787-case run was not repeated. Baseline tests
were not changed. `git diff --check` passed. No tracked .env/private key container
files were found by filename inspection; that is not a content-level secret audit.
pytest-cov is unavailable, so no numerical coverage report was produced.

Do not equate successful synthetic contracts with literary quality, educational
accuracy or complete safety. No confirmed production defect was found by the
new tests; therefore
there are no defect reproduction steps to invent. Reproduce any subsequent
failure with the named pytest node and attach sanitized expected/actual codes,
attempt count and baseline hash, never raw child content or credentials.

## Continuation checklist

1. Review the isolated QA diff and fixture assumptions; no merge is performed.
2. Integrate diagnostics, frontend and persistence through their owning agents.
3. Rerun offline suites, then add actual UI-to-local-fake journeys and disposable
   local database tests without paid providers.
4. Perform native-language manuscript review with QA_HUMAN_REVIEW.md before
   making quality claims. Saving, illustration and exporting remain untested.
5. Keep tracing and child-content logging disabled; no live evaluation is authorized.
