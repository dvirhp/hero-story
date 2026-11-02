# Bounded LangGraph execution (Milestone 3)

> Current Milestone 5 update: OpenAI adapter implemented and tested offline; fake remains the default. Stage-specific model/capability/pricing configuration is explicit. See [provider reference](PROVIDERS.md). Long-term scope is worldwide languages and multiple providers; only Hebrew/English and fake/OpenAI are executable today. See [extension review and proposed follow-up work](EXTENSIBILITY.md). Historical milestone sections below describe their original boundaries. Stop before Milestone 6.

Milestone 3 is implemented with one compiled `StateGraph`, four named nodes and explicit conditional edges. The supported engine entry point is `await StoryEngine(...).generate(request)`. Milestone 4 adds a thin [HTTP application](API.md) around this entry point without changing execution policy. No persistence, checkpoint store, real LLM SDK or remote runtime exists. Framework dependencies include LangGraph's transitive client/checkpoint packages; they are not used to contact or store anything.

## Flow

| Node | Work and destinations |
| --- | --- |
| `input_validation` | Strictly parse a `StoryRequest`, JSON or JSON-compatible dict, then call existing `normalize_request`. Failure → END; valid brief → planner. Zero provider calls on rejection. |
| `story_planner` | Build `planner-v1` instructions and untrusted JSON data; invoke provider once, validate `StoryPlan` and `validate_for(brief)`. Valid → writer; recoverable failure with capacity → planner; terminal/exhausted → END. |
| `story_writer` | Build `writer-v1` using the validated plan and captured profile. Invoke once; validate `Story` and `validate_for(brief)`. Valid → gate; recoverable failure with capacity → writer; terminal/exhausted → END. |
| `quality_gate` | Call existing pure `assess_story`. Pass → accepted success; repairable failure → writer once if capacity remains; terminal or exhausted → END with failure. |

LangGraph's [conditional-edge API](https://reference.langchain.com/python/langgraph/graph/state/StateGraph/add_conditional_edges) supplies the routing. Each provider node has `RetryPolicy(max_attempts=1)` so framework retries cannot bypass the shared ledger. There is no supervisor, separate retry node, nested recovery loop or LLM quality judge. A recursion limit of 16 is a secondary guard.

## State and boundaries

`GraphState` carries one immutable validated `RunState`; each node returns a validated replacement and leaves previous records intact. State holds request ID, raw input until validation, validated request/brief/profile snapshot, plan/draft, report/error, stage/status, attempt records/count, token reservations, rewrite count, monotonic start/deadline, remaining time/tokens/cost, simulated latency offset and configuration versions. Sensitive fields are excluded from state repr. State itself is internal and must not be logged, persisted, streamed to clients or inspected using external tracing.

Request-local `Session.current` is an in-memory journal, not shared engine state or persistence. It captures the pre-await attempt reservation and completion, so cancellation does not lose a potentially billable invocation. One engine can run concurrent requests; provider implementations must independently support their intended concurrent use. A single sequential `FakeProvider` script should not be shared across interleaved unrelated scripts; tests use an explicit routing fake for concurrency.

Only `GenerationSuccess` includes an approved story. `GenerationFailure` contains safe error/quality/usage metadata and never a draft. Recoverable provider diagnostics are replaced by fixed messages; exceptions are not logged. Terminal quality issues take precedence over repairable ones. Profile constraints remain the approved immutable developmental configuration; no orchestration age bands or universal plot are introduced.

## Prompts and recovery

Trusted shared/language instructions are separate from JSON data containing the brief, supplied name/pronouns, plan and optional previous draft. Instructions explicitly forbid treating user guidance as control, infer neither gender nor reading ability, and permit sensory/noticing stories without a conflict. Prompt separation reduces accidental instruction mixing; it does not prove resistance to adversarial inputs.

Schema/context retries receive a concise fixed schema-recovery instruction, never raw failed output or validation exceptions. A quality rewrite receives the previous validated draft, plan and only repairable issue guidance; advisories are not repair obligations. Rewrites must retain page IDs. A schema failure during a rewrite consumes the same final call slot, with no extra rewrite or hidden retry.

Normal path: planner + writer = two invocations. Global maximum: three, including transport exceptions, schema/context recovery and quality rewrite. A planner retry is allowed only when a slot remains for the mandatory writer: two failed planner attempts end without spending the third slot on another plan. At most one quality rewrite is scheduled. If a schema/transport retry spent the extra slot, no quality rewrite remains. Exhausted attempts produce `BUDGET_EXCEEDED`; unaccepted final drafts produce `QUALITY_REJECTED`. No client/HTTP retry is implemented.

## Token, time and cost controls

`AppSettings` retains 1,200 planner-output / 3,000 writer-output tokens, 8,000 input tokens per call, 30 seconds per attempt, 90 seconds overall, and at most three attempts / one rewrite. Settings can lower limits while respecting their existing validation. Each call receives the smaller of per-attempt and remaining overall time. Local `asyncio.timeout` guards enforce cooperative wall-clock cancellation; the injected monotonic clock supports deterministic deadline tests.

`BudgetLimits` adds versioned aggregate token and cost ceilings: initially 33,000 tokens and USD 0 under the explicitly synthetic `fake-zero-v1` tariff. `FakePricing` accepts versioned synthetic input/output USD-per-million rates for accounting tests; positive rates need an explicitly sufficient cost ceiling. These are fake configuration values, not real-provider pricing or a product spend decision.

Input reservation policy `fake-utf8-bytes-v1` counts one unit per UTF-8 byte of instructions, JSON input and requested output schema, plus 256 configurable overhead units. This conservative **fake policy** is not a universal model tokenizer. Each call reserves that input bound plus its entire output cap. A planner call additionally verifies that remaining token/cost capacity can cover a writer at the configured worst-case input/output caps. Future-stage capacity is checked without recording an invocation that has not occurred.

Reservations remain held through the request; successful reported usage does not free capacity for more calls. Known input/output counts exceeding the reservation/cap terminate with `BUDGET_EXCEEDED`; their reported usage/cost still remains in the ledger. All attempts, including thrown exceptions, timeouts and cancellations, consume slots. Output token limits are passed to the adapter and checked against supplied known usage; unknown usage cannot certify actual output token counts. Real tokenizer/context and rate-table validation remains Milestone 5 and must replace this fake policy before paid use.

Known usage is recorded as reported/estimated with a pricing version and calculated cost. Unknown counts stay `None`, estimated cost stays `None`, and the conservative token/cost reservation remains. `known_estimated_cost_usd` is only the known subtotal; it is never the total bill when `has_unknown_usage` is true. `upper_estimated_cost_usd` sums held reservations (expanded if a report exceeds them), and is a configured estimate, not a billing guarantee. Under a zero fake tariff this upper cost is zero even while token usage is explicitly unknown.

Record per-call latency as the maximum of measured and supplied latency. Fake-supplied latency advances a virtual offset without sleeping, so overall fake deadlines cannot be bypassed by immediate scripted responses. End-to-end latency includes local work and this offset. Injected clock values must be monotonic. Cancellation returns a typed `CANCELLED` failure and retains the ledger; it does not re-raise `CancelledError` at the public wrapper. An attempt timeout can retry within the shared budget if overall time remains. Overall timeout prevents all further calls. Remote cancellation/billing guarantees are outside this fake-only milestone.

## Compatible provider-failure extension

Milestone 1 adapters erased malformed responses after schema validation, which prevented orchestration from recognizing terminal unsafe content inside them. The smallest compatible change adds optional `ProviderFailure.quality: QualityReport | None`. `FakeProvider` now reuses Milestone 2's narrow safety checks before schema parsing and returns only a sanitized terminal report, never raw response text. Existing constructors and protocol method signatures remain compatible; all original tests remain unchanged. Success payloads are also checked by orchestration before context validation.

When customizing rules, pass the same immutable `QualityRules` to `FakeProvider(..., rules=rules)` and `StoryEngine(..., rules=rules)`. Schema-invalid unsafe responses terminate without a repair. Detection has the same narrow literal/context limitations as [Milestone 2](VALIDATION_AND_QUALITY.md), particularly undecodable JSON fragments. No broad moderation guarantee is introduced. Fake transient failures retry immediately through explicit graph edges; real Retry-After/backoff metadata is deferred to the real adapter milestone.

External tracing is explicitly disabled around public generation, including environment-enabled LangSmith tracing. No callbacks, checkpoints or remote tracing are configured. Access to `engine.graph` is for local development/inspection; invoke the supported wrapper to establish budgets and sanitized results.

## Local commands and Git discipline

From the repository root in Windows PowerShell, after the README setup:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.tools\Scripts\uv.exe run --python 3.12 --isolated --locked python -m pytest -q
.\.venv\Scripts\python.exe -m storyforge.demo --language he --age-months 0
.\.venv\Scripts\python.exe -m storyforge.demo --language en --age-months 180
.\.tools\Scripts\uv.exe build
```

The demo uses synthetic names and scripted fixture text, not paid/generated literature. It prints only status, request ID, profile, attempt count and usage/cost metadata. Quality acceptance remains a limited deterministic result, not a literary-quality claim.

Milestone 3 work is recorded on `feature/milestone-3-langgraph`; Milestone 4 continues on `feature/milestone-4-fastapi`. Git was initialized from the tested Milestone 2 source baseline using the existing author identity. No identity or credential settings were changed; no remote was created. Environments, `.env` variants (except sample/template files), key files, caches, generated archives and build artifacts are ignored. For future changes: inspect status/diff, make a small coherent change, run relevant tests, review staged files, then commit with a meaningful `feat:`, `fix:`, `test:`, `docs:` or `chore:` message. Never create empty commits, commit failing changes or include sensitive content. No pushes or deployment without user approval.

Open decisions remain model/provider selection, real tokenizer/capacity/pricing validation and spend ceiling, bilingual prompt evaluation, reviewed moderation expansion and human release criteria. Milestone 4's HTTP layer is separate from this engine and has its own approved local branch; do not begin real providers (Milestone 5) without approval.
