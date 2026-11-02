"""Four explicit nodes, one shared ledger, no hidden or nested retry loops."""

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import RetryPolicy
from langsmith import tracing_context
from pydantic import ValidationError

from storyforge.config import AppSettings
from storyforge.development.models import DevelopmentConfig
from storyforge.domain.base import Contract
from storyforge.domain.generation import (
    AttemptRecord, GenerationError, GenerationFailure, GenerationResult,
    GenerationSuccess, QualityReport, TokenUsage,
)
from storyforge.domain.story import Story, StoryPlan, StoryRequest
from storyforge.llm.protocol import LLMProvider, LLMRequest, ProviderFailure
from storyforge.llm.configuration import ModelCapabilities
from storyforge.orchestration.budget import BudgetLimits, FakePricing, ModelPricing, reservation_policy
from storyforge.orchestration.state import GraphState, RunState
from storyforge.prompts.builders import PLANNER_VERSION, WRITER_VERSION, build_request
from storyforge.quality.gate import assess_story, inspect_output_safety
from storyforge.quality.rules import DEFAULT_RULES, QualityRules
from storyforge.validation.normalization import NormalizationError, normalize_request


@dataclass
class Session:
    # Request-local journal survives node cancellation before a graph update.
    current: RunState


def _error(code: str, stage: str, retryable: bool = False) -> GenerationError:
    messages = {
        "INPUT_INVALID": "Request does not match the supported input contract",
        "POLICY_REJECTED": "Prohibited content or controls were detected",
        "PROVIDER_OUTPUT_INVALID": "Provider output did not match the stage contract",
        "PROVIDER_UNAVAILABLE": "Provider temporarily unavailable",
        "PROVIDER_REFUSED": "Provider declined this request",
        "CONFIGURATION_ERROR": "Execution dependency failed; review local configuration",
        "DEADLINE_EXCEEDED": "Execution deadline exceeded",
        "CANCELLED": "Generation cancelled",
        "BUDGET_EXCEEDED": "Insufficient attempt, token or cost budget",
        "QUALITY_REJECTED": "Draft failed the configured deterministic quality checks",
    }
    return GenerationError(code=code, stage=stage, retryable=retryable, message=messages[code])


class StoryEngine:
    def __init__(
        self, provider: LLMProvider, profiles: DevelopmentConfig, *,
        settings: AppSettings = AppSettings(), limits: BudgetLimits = BudgetLimits(),
        pricing: FakePricing | ModelPricing = FakePricing(), rules: QualityRules = DEFAULT_RULES,
        clock: Callable[[], float] = time.monotonic,
        capabilities: ModelCapabilities | None = None,
        writer_capabilities: ModelCapabilities | None = None,
        writer_pricing: ModelPricing | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.provider, self.profiles = provider, profiles
        self.settings, self.limits, self.pricing, self.rules, self.clock = settings, limits, pricing, rules, clock
        self.capabilities, self.sleep = capabilities, sleep
        self.input_bound = reservation_policy(settings.provider)
        if getattr(provider, "provider_name", settings.provider) != settings.provider:
            raise ValueError("Provider identity must match explicit application settings")
        self.writer_capabilities = writer_capabilities or capabilities
        self.writer_pricing = writer_pricing or pricing
        if settings.provider != "fake":
            for stage in ("planner", "writer"):
                cap, tariff = self._stage_capabilities(stage), self._stage_pricing(stage)
                output = settings.planner_output_tokens if stage == "planner" else settings.writer_output_tokens
                if (cap is None or cap.model != settings.model_for(stage) or not isinstance(tariff, ModelPricing)
                        or tariff.model != settings.model_for(stage) or tariff.provider != settings.provider
                        or limits.max_cost_usd <= 0):
                    raise ValueError("Real execution requires matching stage capabilities, pricing and positive cost ceiling")
                if settings.max_input_tokens + output > cap.context_tokens or output > cap.max_output_tokens:
                    raise ValueError("Configured token limits exceed declared model capacity")
        graph = StateGraph(GraphState, context_schema=Session)
        for name, node in (("input_validation", self._validate), ("story_planner", self._planner),
                           ("story_writer", self._writer), ("quality_gate", self._quality)):
            graph.add_node(name, node, retry_policy=RetryPolicy(max_attempts=1))
        graph.add_edge(START, "input_validation")
        graph.add_conditional_edges("input_validation", self._after_validation,
                                    {"plan": "story_planner", "end": END})
        graph.add_conditional_edges("story_planner", self._after_planner,
                                    {"retry": "story_planner", "write": "story_writer", "end": END})
        graph.add_conditional_edges("story_writer", self._after_writer,
                                    {"retry": "story_writer", "check": "quality_gate", "end": END})
        graph.add_conditional_edges("quality_gate", self._after_quality,
                                    {"rewrite": "story_writer", "end": END})
        self.graph = graph.compile()  # No persistence, caching, or remote runtime.

    def _stage_capabilities(self, stage: str) -> ModelCapabilities | None:
        return self.writer_capabilities if stage == "writer" else self.capabilities

    def _stage_pricing(self, stage: str) -> FakePricing | ModelPricing:
        return self.writer_pricing if stage == "writer" else self.pricing

    def _refresh(self, run: RunState) -> RunState:
        return run.updated(
            remaining_seconds=max(0.0, run.deadline - self.clock() - run.simulated_seconds),
            remaining_tokens=max(0, self.limits.max_total_tokens - sum(run.token_reservations)),
            remaining_cost_usd=max(0.0, self.limits.max_cost_usd - sum(a.reserved_cost_usd for a in run.attempts)),
        )

    def _fail(self, run: RunState, code: str) -> RunState:
        return run.updated(status="failure", error=_error(code, run.stage))

    @staticmethod
    def _publish(run: RunState, session: Session) -> GraphState:
        session.current = run
        return {"run": run}

    def _validate(self, state: GraphState, runtime: Runtime[Session]) -> GraphState:
        run = self._refresh(state["run"])
        if run.remaining_seconds <= 0:
            return self._publish(self._fail(run, "DEADLINE_EXCEEDED"), runtime.context)
        try:
            raw = run.raw_input
            if isinstance(raw, StoryRequest):
                request = raw
            elif isinstance(raw, str):
                request = StoryRequest.model_validate_json(raw)
            elif isinstance(raw, dict):
                request = StoryRequest.model_validate_json(json.dumps(raw, ensure_ascii=True, allow_nan=False))
            else:
                raise ValueError("unsupported input representation")
            brief = normalize_request(request, self.profiles, self.rules)
            run = run.updated(raw_input=None, request=brief.request, brief=brief)
        except NormalizationError as exc:
            run = run.updated(raw_input=None, status="failure", error=exc.error)
        except (ValueError, TypeError, RecursionError):
            run = self._fail(run.updated(raw_input=None), "INPUT_INVALID")
        return self._publish(run, runtime.context)

    async def _attempt(
        self, run: RunState, request: LLMRequest, schema: type[Contract], session: Session,
    ) -> tuple[RunState, Contract | None]:
        run = self._refresh(run)
        if run.retry_after_seconds:
            if run.retry_after_seconds >= run.remaining_seconds:
                return self._fail(run, "DEADLINE_EXCEEDED"), None
            await self.sleep(run.retry_after_seconds)
            run = self._refresh(run.updated(retry_after_seconds=0.0))
        if run.remaining_seconds <= 0:
            return self._fail(run, "DEADLINE_EXCEEDED"), None
        capabilities = self._stage_capabilities(request.stage)
        overhead = capabilities.input_overhead_tokens if capabilities else self.limits.schema_overhead_tokens
        tokens_in = self.input_bound(request, schema, overhead)
        reserve_tokens = tokens_in + request.max_output_tokens
        reserve_cost = self._stage_pricing(request.stage).reservation_cost(tokens_in, request.max_output_tokens)
        future_tokens = (self.settings.max_input_tokens + self.settings.writer_output_tokens
                         if request.stage == "planner" else 0)
        future_cost = (self.writer_pricing.reservation_cost(self.settings.max_input_tokens, self.settings.writer_output_tokens)
                       if request.stage == "planner" else 0.0)
        required_slots = 2 if request.stage == "planner" else 1
        if (tokens_in > self.settings.max_input_tokens
                or run.attempts_used + required_slots > self.settings.max_attempts
                or reserve_tokens + future_tokens > run.remaining_tokens
                or reserve_cost + future_cost > run.remaining_cost_usd):
            return self._fail(run, "BUDGET_EXCEEDED"), None
        duration_limit = min(self.settings.attempt_timeout_seconds, run.remaining_seconds)
        request = LLMRequest.model_validate({**request.model_dump(), "remaining_seconds": duration_limit})
        reserved = AttemptRecord(
            stage=request.stage, attempt_number=run.attempts_used + 1, provider=self.settings.provider, model=request.model,
            prompt_version=request.prompt_version, latency_seconds=0.0, usage=TokenUsage(source="unknown"),
            reserved_cost_usd=reserve_cost, pricing_version=self._stage_pricing(request.stage).version, outcome="failure",
            error=_error("CANCELLED", request.stage),
        )
        run = run.updated(attempts=(*run.attempts, reserved), attempts_used=run.attempts_used + 1,
                          token_reservations=(*run.token_reservations, reserve_tokens))
        session.current = run  # Slot and conservative charge exist before any await.
        started = self.clock()
        usage = TokenUsage(source="unknown")
        latency = 0.0
        payload = None
        error = None
        quality = run.quality
        retry_after = 0.0
        try:
            async with asyncio.timeout(duration_limit):
                response = await self.provider.generate(request, schema)
            usage, latency = response.usage, response.latency_seconds
            if isinstance(response, ProviderFailure):
                code = response.error.code
                recoverable = (code in ("PROVIDER_UNAVAILABLE", "PROVIDER_OUTPUT_INVALID", "DEADLINE_EXCEEDED")
                               and response.error.retryable)
                error = _error(code, request.stage, recoverable)
                retry_after = response.retry_after_seconds or 0.0
                if response.quality and any(i.severity == "terminal" for i in response.quality.issues):
                    quality = response.quality
                    error = _error("POLICY_REJECTED", request.stage)
            else:
                # Revalidate typed data; never trust a model_copy or model_construct.
                payload = schema.model_validate(response.payload.model_dump(warnings=False))
                unsafe = inspect_output_safety(payload.model_dump(), self.rules)
                if unsafe:
                    quality = QualityReport(passed=False, issues=unsafe, check_version=self.rules.version,
                                            rubric_version=self.rules.rubric_version)
                    error = _error("POLICY_REJECTED", request.stage)
                    payload = None
                else:
                    payload.validate_for(run.brief)
                    if (request.stage == "writer" and run.rewrite_count and run.draft is not None
                            and tuple(page.page_id for page in payload.pages)
                            != tuple(page.page_id for page in run.draft.pages)):
                        raise ValueError("rewrite must preserve request-local page IDs")
            if latency > duration_limit and error is None:
                error, payload = _error("DEADLINE_EXCEEDED", request.stage, True), None
            if (usage.source != "unknown" and (usage.input_tokens > tokens_in
                    or usage.output_tokens > request.max_output_tokens)):
                error, payload = _error("BUDGET_EXCEEDED", request.stage), None
        except asyncio.CancelledError:
            latency = max(0.0, self.clock() - started)
            session.current = self._complete_attempt(run, reserved, usage, latency,
                                                     _error("CANCELLED", request.stage), quality, started)
            raise
        except TimeoutError:
            error = _error("DEADLINE_EXCEEDED", request.stage, True)
        except (ConnectionError, OSError):
            error = _error("PROVIDER_UNAVAILABLE", request.stage, True)
        except (ValidationError, ValueError):
            error = _error("PROVIDER_OUTPUT_INVALID", request.stage, True)
        except Exception:
            error = _error("CONFIGURATION_ERROR", request.stage)
        latency = max(latency, self.clock() - started)
        run = self._complete_attempt(run, reserved, usage, latency, error, quality, started)
        run = run.updated(retry_after_seconds=retry_after)
        if run.remaining_seconds <= 0:
            run = self._fail(run, "DEADLINE_EXCEEDED")
            payload = None
        if run.remaining_tokens == 0 and payload is None:
            run = self._fail(run, "BUDGET_EXCEEDED")
        session.current = run
        return run, payload if error is None and run.status != "failure" else None

    def _complete_attempt(
        self, run: RunState, reserved: AttemptRecord, usage: TokenUsage, latency: float,
        error: GenerationError | None, quality: QualityReport | None, started: float,
    ) -> RunState:
        cost = self._stage_pricing(reserved.stage).usage_cost(usage)
        reserve_cost = max(reserved.reserved_cost_usd, cost or 0.0)
        actual_tokens = ((usage.input_tokens + usage.output_tokens) if usage.source != "unknown" else 0)
        record = AttemptRecord.model_validate({
            **reserved.model_dump(), "usage": usage, "latency_seconds": latency,
            "estimated_cost_usd": cost, "reserved_cost_usd": reserve_cost,
            "outcome": "failure" if error else "success", "error": error,
        })
        simulated = max(0.0, latency - max(0.0, self.clock() - started))
        return self._refresh(run.updated(
            attempts=(*run.attempts[:-1], record),
            token_reservations=(*run.token_reservations[:-1], max(run.token_reservations[-1], actual_tokens)),
            simulated_seconds=run.simulated_seconds + simulated, error=error, quality=quality,
        ))

    def _settle_failure(self, run: RunState) -> RunState:
        run = self._refresh(run)
        if run.remaining_seconds <= 0:
            return self._fail(run, "DEADLINE_EXCEEDED")
        if run.status == "failure" or not run.error.retryable:
            return run.updated(status="failure")
        required_slots = 2 if run.stage == "planner" else 1
        if run.attempts_used + required_slots > self.settings.max_attempts:
            return self._fail(run, "BUDGET_EXCEEDED")
        return run  # Conditional self-edge schedules the sole retry mechanism.

    async def _planner(self, state: GraphState, runtime: Runtime[Session]) -> GraphState:
        run = self._refresh(state["run"].updated(stage="planner"))
        request = build_request("planner", run.brief, self.settings.model_for("planner"), self.settings.planner_output_tokens,
                                max(0.000001, run.remaining_seconds), schema_recovery=run.error is not None)
        run, plan = await self._attempt(run, request, StoryPlan, runtime.context)
        run = run.updated(plan=plan, error=None) if plan is not None else self._settle_failure(run)
        return self._publish(run, runtime.context)

    async def _writer(self, state: GraphState, runtime: Runtime[Session]) -> GraphState:
        run = self._refresh(state["run"].updated(stage="writer"))
        try:
            request = build_request("writer", run.brief, self.settings.model_for("writer"), self.settings.writer_output_tokens,
                                    max(0.000001, run.remaining_seconds), plan=run.plan,
                                    draft=run.draft if run.rewrite_count else None,
                                    quality=run.quality if run.rewrite_count else None,
                                    schema_recovery=run.error is not None)
        except ValidationError:
            return self._publish(self._fail(run, "BUDGET_EXCEEDED"), runtime.context)
        run, draft = await self._attempt(run, request, Story, runtime.context)
        run = run.updated(draft=draft, error=None) if draft is not None else self._settle_failure(run)
        return self._publish(run, runtime.context)

    def _quality(self, state: GraphState, runtime: Runtime[Session]) -> GraphState:
        run = self._refresh(state["run"].updated(stage="quality"))
        if run.remaining_seconds <= 0:
            return self._publish(self._fail(run, "DEADLINE_EXCEEDED"), runtime.context)
        report = assess_story(run.draft, run.brief, self.rules)
        run = run.updated(quality=report)
        if report.passed:
            run = run.updated(status="success", error=None)
        elif (any(i.severity == "terminal" for i in report.issues)
              or run.rewrite_count >= self.settings.max_quality_rewrites
              or run.attempts_used >= self.settings.max_attempts):
            run = self._fail(run, "QUALITY_REJECTED")
        else:
            run = run.updated(rewrite_count=run.rewrite_count + 1, error=None)
        return self._publish(self._refresh(run), runtime.context)

    @staticmethod
    def _after_validation(state: GraphState) -> Literal["plan", "end"]:
        return "end" if state["run"].status == "failure" else "plan"

    @staticmethod
    def _after_planner(state: GraphState) -> Literal["retry", "write", "end"]:
        run = state["run"]
        return "end" if run.status == "failure" else "write" if run.plan else "retry"

    @staticmethod
    def _after_writer(state: GraphState) -> Literal["retry", "check", "end"]:
        run = state["run"]
        return "end" if run.status == "failure" else "retry" if run.error else "check"

    @staticmethod
    def _after_quality(state: GraphState) -> Literal["rewrite", "end"]:
        return "rewrite" if state["run"].status == "running" else "end"

    async def generate(self, request: object, *, request_id: str | None = None) -> GenerationResult:
        started = self.clock()
        run = RunState(
            request_id=request_id or str(uuid4()), raw_input=request, started_at=started,
            deadline=started + self.settings.request_timeout_seconds,
            remaining_seconds=self.settings.request_timeout_seconds,
            remaining_tokens=self.limits.max_total_tokens, remaining_cost_usd=self.limits.max_cost_usd,
            versions=(("profiles", self.profiles.version), ("quality", self.rules.version),
                      ("rubric", self.rules.rubric_version), ("pricing", self.pricing.version),
                      ("budget", self.limits.version),
                      ("writer_pricing", self.writer_pricing.version),
                      ("writer_capabilities", self.writer_capabilities.version if self.writer_capabilities else "fake-v1"),
                      ("token_bound", self.capabilities.token_bound_version if self.capabilities else self.limits.token_bound_version),
                      ("model_capabilities", self.capabilities.version if self.capabilities else "fake-v1"),
                      ("settings_schema", "settings-v1"),
                      ("planner_prompt", PLANNER_VERSION), ("writer_prompt", WRITER_VERSION)),
        )
        session = Session(run)
        try:
            # Explicitly prevent environment-enabled tracing from exporting child data.
            with tracing_context(enabled=False):
                async with asyncio.timeout(self.settings.request_timeout_seconds):
                    output = await self.graph.ainvoke({"run": run}, context=session,
                                                     config={"recursion_limit": 16, "callbacks": []})
            run = output["run"]
        except asyncio.CancelledError:
            run = self._fail(session.current, "CANCELLED")
        except TimeoutError:
            run = self._fail(session.current, "DEADLINE_EXCEEDED")
        except Exception:
            run = self._fail(session.current, "CONFIGURATION_ERROR")
        run = self._refresh(run)
        if run.remaining_seconds <= 0 and (run.error is None or run.error.code != "CANCELLED"):
            run = self._fail(run, "DEADLINE_EXCEEDED")
        total = max(0.0, self.clock() - run.started_at + run.simulated_seconds)
        common = dict(request_id=run.request_id, usage=run.usage(), total_latency_seconds=total)
        if run.status == "success":
            return GenerationSuccess(**common, story=run.draft, quality=run.quality)
        return GenerationFailure(**common, error=run.error or _error("CONFIGURATION_ERROR", run.stage),
                                 quality=run.quality)
