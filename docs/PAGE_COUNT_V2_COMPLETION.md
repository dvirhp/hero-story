# Page-count v2 completion

Approved Milestone 6 follow-up completed on branch
`feature/milestone-6-page-count-v2`. Stop before Milestone 7 and any further live
request. [Contracts and migration](PAGE_COUNT_V2.md) are the current reference.

## Changed files

| Area | Added or updated files |
| --- | --- |
| Domain | `domain/story_v2.py`, `domain/generation_v2.py` |
| Developmental configuration | `development/v2.py`, `development/profiles.v2.json` |
| Normalization and sizing | `validation/normalization_v2.py`, `validation/page_policy.py` |
| Orchestration | `orchestration/contracts.py`, `orchestration/engine.py`, `orchestration/state.py` |
| Prompts and quality | `prompts/v2.py`, `quality/gate.py` |
| Offline fixtures | `llm/fixtures_v2.py`, `llm/fixtures.py` |
| API | `api/routes_v2.py`, `api/routes.py`, `api/app.py`, `api/dependencies.py`, `api/configured.py`, `api/execution.py` |
| Tests | `tests/test_v2_contracts.py`, `tests/test_v2_execution.py`, `tests/test_v2_providers.py` |
| Acceptance inputs | `docs/examples/roy-alphabet-request.v2.he.json`, `docs/examples/roy-alphabet-runtime.v2.proposed.json` |
| Planning and reference | `AGENTS.md`, `README.md`, Product Spec, Architecture, AI Design, Roadmap, API, Orchestration, Validation and Quality, Providers, Gemini, Extensibility, old alphabet proposal README, `PAGE_COUNT_V2.md`, this report |

Source paths above are relative to `src/storyforge/` unless prefixed with
`tests/`, `docs/`, or named as root documents. Existing v1 schemas/profile data,
real provider adapters, dependency lock and original newborn smoke runtime are
unchanged. All 544 preceding tests remain unchanged.

## Decisions and API impact

- V2 requires a strict explicit page count. Configurable admission defaults to
  1–32; neither age nor the LLM can change the requested count. Automatic mode is
  not implemented.
- Five versioned developmental profiles own language strategy and light/standard
  page density, not total book length. Guidance and density values remain
  provisional product hypotheses.
- Generic ordered learning targets support alphabet and other educational books;
  orchestration contains no Hebrew alphabet or Roy-specific branches.
- Four graph nodes, provider protocol/adapters, independent stage models,
  attempt ledger, cost reservations, deadline/cancellation and maximum three
  attempts/one rewrite are preserved.
- `/v2/stories/generate` returns `StoryV2` with sentence units and resolved
  constraints. Clients join sentence units to render text. `/v1` stays deprecated
  with isolated original behavior; no retirement date is chosen.
- Planner/Writer prompts request age-appropriate repetition and varied progression.
  Deterministic checks validate structure and literal educational coverage;
  fluency, meaningful progression, teaching accuracy and agency need human review.

## Verification

| Environment/check | Result |
| --- | --- |
| Windows, Python 3.13.3, source checkout | **750 passed, 0 failed**, 114.23 seconds |
| Windows, Python 3.12.16, isolated installed wheel | **750 passed, 0 failed**, 72.95 seconds |
| Earlier locked isolated Python 3.12 source run before final extra cases | 729 passed, 0 failed |
| New v2 cases | 206 total: contracts 117, execution/API/quality 83, adapter/preflight 6 |
| Source and wheel builds | Passed |
| Installed package location/resource check | Imports from isolated `site-packages`; `profiles.v2.json` loads |
| Roy proposed-runtime preflight | Passed offline; complete planner/writer/recovery budget fits |
| README default v2 fake request | Success with four requested pages |
| Distribution inspection | V2 route/profile data included; real `.env`, environments and caches excluded |

Pytest blocks network sockets. OpenAI/Gemini adapter tests use dummy keys and
HTTPX mock transports; no live requests or local credential reads were needed.
No new dependencies, billing changes, Cloud changes, push, deployment, database,
frontend, automatic continuation or Milestone 7 work were introduced.

Exact standard PowerShell setup/test/build commands:

```powershell
py -m venv .tools
.\.tools\Scripts\python.exe -m pip install uv==0.13.6
.\.tools\Scripts\uv.exe sync --locked
.\.venv\Scripts\python.exe -m pytest -q
.\.tools\Scripts\uv.exe run --python 3.12 --isolated --locked python -m pytest -q
.\.tools\Scripts\uv.exe build
```

Installed-wheel verification used a separate ignored environment:

```powershell
.\.tools\Scripts\uv.exe export --locked --no-emit-project --format requirements-txt --output-file .tools/page-count-v2-dependencies.txt
.\.tools\Scripts\uv.exe venv .tools/page-count-v2-wheel --python 3.12
.\.tools\Scripts\uv.exe pip install --python .tools/page-count-v2-wheel/Scripts/python.exe --requirement .tools/page-count-v2-dependencies.txt dist/storyforge_ai-0.1.0-py3-none-any.whl
.\.tools\page-count-v2-wheel\Scripts\python.exe -m pytest -q
```

Use an unused environment directory when reproducing isolated installation.
Tests and builds require no paid-provider credentials.

## Roy live test remains pending

The exact v2 request is prepared, including 27 ordered letters, age 36 months,
12–24 words/page and 2–3 sentence units. Offline synthetic output is not the
requested finished story and does not establish semantic educational acceptance.

Before a live run, verify current official model availability/schema support,
pricing/capabilities and reservation overhead; explicitly approve the exact
request/pronouns and isolated runtime limits. The proposed runtime uses 3,000 /
6,000 output ceilings, 32,000 input per call, 111,000 aggregate tokens, 45 seconds
per attempt / 135 overall, three shared attempts and one rewrite, with a $0.075
internal request ceiling. The resolved output caps are 2,792 / 4,128.

At the inherited declared prices, mandatory two-stage full-cap reservation is
$0.03650; the largest three-attempt path reserves $0.05642 and 107,048 tokens.
These are estimates, not verified current prices or guaranteed billing limits.
The original $0.015 newborn ceiling is unchanged and rejects this request.
No proposed larger budget has been activated or approved for live execution.

After explicit approval, send exactly one end-to-end POST to `/v2/stories/generate`
using the prepared request and reviewed isolated runtime; do not automatically
repeat it. Report stage outcomes, gate result, attempts, tokens, cost, latency,
errors and successful story. Human review must check Hebrew sentences, correct
word-final teaching, Roy's agency, variety, continuity and read-aloud suitability.

Remaining product decisions: v1 retirement timing; density/sizing calibration;
older-child refinements; semantic evaluation/release thresholds; future automatic
length, additional language packs and providers. No such decision was silently
implemented.
