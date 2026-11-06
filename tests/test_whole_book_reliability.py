"""Whole-book contracts and recovery with deterministic time; no network calls."""

import asyncio
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from storyforge.api.configured import RuntimeConfiguration
from storyforge.config import AppSettings
from storyforge.development.v2 import load_profiles_v2
from storyforge.domain.diagnostics import ProviderDiagnostic
from storyforge.domain.generation import GenerationError, TokenUsage
from storyforge.domain.story_v2 import StoryRequestV2, StoryV2
from storyforge.llm.fake import FakeProvider, FakeStep
from storyforge.llm.fixtures_v2 import fixture_steps_v2
from storyforge.llm.protocol import ProviderFailure
from storyforge.orchestration.budget import BudgetLimits
from storyforge.orchestration.engine import StoryEngine
from storyforge.orchestration.recovery import RetrySettings
from storyforge.quality.gate import assess_story
from storyforge.validation.normalization_v2 import normalize_v2


EXAMPLES = Path(__file__).resolve().parents[1] / "docs" / "examples"
SETTINGS = AppSettings(planner_output_tokens=6144, writer_output_tokens=16384, max_input_tokens=32000)
LIMITS = BudgetLimits(max_total_tokens=140000)


class Clock:
    now = 0.0

    def __init__(self):
        self.waits = []

    def __call__(self):
        return self.now

    async def sleep(self, delay):
        self.waits.append(delay)
        self.now += delay


class ScriptedProvider:
    def __init__(self, steps):
        self.steps = iter(steps)
        self.calls = []

    async def generate(self, request, schema):
        self.calls.append(request)
        step = next(self.steps)
        if isinstance(step, ProviderFailure):
            assert step.error.stage == request.stage
            return step
        return await FakeProvider((step,)).generate(request, schema)


def failure(code="PROVIDER_UNAVAILABLE", category="server_error", delay=None, stage="writer"):
    return ProviderFailure(provider="fake", model="scripted-v1", usage=TokenUsage(source="unknown"),
                           latency_seconds=0.0, retry_after_seconds=delay,
                           provider_diagnostic=ProviderDiagnostic(category=category,
                               upstream_http_status=503 if category == "server_error" else None),
                           error=GenerationError(code=code, stage=stage, retryable=True, message="Synthetic failure"))


def roy():
    return StoryRequestV2.model_validate_json((EXAMPLES / "roy-alphabet-request.v2.he.json").read_text(encoding="utf-8"))


def context(req, settings=SETTINGS):
    return normalize_v2(req, load_profiles_v2(), settings=settings)


def execute(run_async, profiles, req, steps, *, settings=SETTINGS, limits=LIMITS, clock=None):
    provider = ScriptedProvider(steps)
    clock = clock or Clock()
    engine = StoryEngine(provider, profiles, settings=settings, limits=limits, contract_version="2",
                         clock=clock, sleep=clock.sleep, random_value=lambda: 0.0)
    return run_async(engine.generate(req)), provider, clock


@pytest.mark.parametrize("language", ["he", "en"])
@pytest.mark.parametrize("age", [0, 3, 12, 36, 72, 10000])
@pytest.mark.parametrize("density", ["light", "standard"])
def test_32_page_capacity_and_max_density_book(run_async, profiles, language, age, density):
    req = StoryRequestV2(language=language, display_name="אור לי" if language == "he" else "Or Lee",
                         age_months=age, page_count=32, theme="Night", text_density=density)
    brief = context(req)
    plan, story = fixture_steps_v2(brief)
    raw = json.loads(story.response_json)
    for page in raw["pages"]:
        words = page["sentence_units"][0].split()
        words.extend(["אור" if language == "he" else "light"] * (brief.constraints.words_per_page.maximum - len(words)))
        # Three entries exercise JSON overhead as well as the upper word range.
        a, b = len(words) // 3, 2 * len(words) // 3
        page["sentence_units"] = [" ".join(words[:a]), " ".join(words[a:b]), " ".join(words[b:])]
    candidate = StoryV2.model_validate_json(json.dumps(raw)).validate_for(brief)
    assert assess_story(candidate, brief).passed
    result, provider, clock = execute(run_async, profiles, req,
        (plan, FakeStep(response_json=candidate.model_dump_json())))
    assert result.status == "success" and result.quality.passed
    assert result.story.page_count == len(result.story.pages) == 32
    assert result.story.direction == ("rtl" if language == "he" else "ltr")
    assert [p.page_number for p in result.story.pages] == list(range(1, 33))
    assert len({p.page_id for p in result.story.pages}) == 32
    assert all(req.display_name in p.text for p in result.story.pages)
    assert len(provider.calls) == 2 and not clock.waits


def test_roy_exact_targets_personalization_and_entries(run_async, profiles):
    req = roy()
    result, provider, _ = execute(run_async, profiles, req, fixture_steps_v2(context(req)))
    assert result.status == "success" and len(provider.calls) == 2
    assert result.story.title == req.requested_title and result.story.page_count == 27
    for target, page in zip(req.structure.targets, result.story.pages, strict=True):
        assert page.target_id == target.target_id and target.label in page.text
        assert req.display_name in page.text and 2 <= len(page.sentence_units) <= 3
        if target.base_form:
            assert target.base_form in page.text and target.example_word in page.text


@pytest.mark.parametrize("language", ["he", "en"])
@pytest.mark.parametrize("mutation", [None, "reordered_targets", "missing_page", "duplicate_id"])
def test_32_ordered_targets_are_complete_or_fail_closed(run_async, profiles, language, mutation):
    raw_request = dict(language=language, display_name="Roy", age_months=36, theme="Discovery",
                       page_count=32, text_density="light", story_type="educational", structure={
                           "targets": [{"target_id": f"target-{i}", "label": f"{'אור' if language == 'he' else 'light'} {i}"}
                                       for i in range(1, 33)],
                           "sentence_units_per_page": {"minimum": 2, "maximum": 3}})
    req = StoryRequestV2.model_validate_json(json.dumps(raw_request))
    plan, story = fixture_steps_v2(context(req))
    raw = json.loads(story.response_json)
    if mutation == "reordered_targets":
        raw["pages"][0]["target_id"], raw["pages"][1]["target_id"] = raw["pages"][1]["target_id"], raw["pages"][0]["target_id"]
    elif mutation == "missing_page":
        raw["pages"].pop()
        raw["page_count"] -= 1
    elif mutation == "duplicate_id":
        raw["pages"][1]["page_id"] = raw["pages"][0]["page_id"]
    step = FakeStep(response_json=json.dumps(raw))
    result, provider, _ = execute(run_async, profiles, req, (plan, step, step))
    if mutation:
        assert result.status == "failure" and len(provider.calls) == 3
        assert not hasattr(result, "story")
    else:
        assert result.status == "success" and len(provider.calls) == 2
        assert tuple(p.target_id for p in result.story.pages) == tuple(t.target_id for t in req.structure.targets)
        assert all(req.display_name in p.text for p in result.story.pages)


@pytest.mark.parametrize("code,category", [("PROVIDER_UNAVAILABLE", "server_error"),
    ("PROVIDER_UNAVAILABLE", "connection_error"), ("DEADLINE_EXCEEDED", "timeout")])
def test_transport_retries_keep_semantic_payload_without_schema_recovery(run_async, profiles, code, category):
    req = roy()
    plan, story = fixture_steps_v2(context(req))
    result, provider, clock = execute(run_async, profiles, req, (plan, failure(code, category), story))
    assert result.status == "success" and len(result.usage.attempts) == 3
    assert provider.calls[1].input_json == provider.calls[2].input_json
    assert "schema_recovery" not in json.loads(provider.calls[2].input_json)
    assert clock.waits == [0.5] and result.total_latency_seconds == 0.5
    assert result.usage.has_unknown_usage and result.usage.attempts[1].provider_diagnostic.category == category


def test_retry_after_is_not_shortened_by_backoff_cap(run_async, profiles):
    req = roy()
    plan, story = fixture_steps_v2(context(req))
    result, _, clock = execute(run_async, profiles, req, (plan, failure(delay=12.0), story))
    assert result.status == "success" and clock.waits == [12.0]
    assert result.total_latency_seconds == 12.0


def test_retry_after_that_cannot_fit_stops_without_waiting_or_dispatch(run_async, profiles):
    req = roy()
    plan, _ = fixture_steps_v2(context(req))
    result, provider, clock = execute(run_async, profiles, req, (plan, failure(delay=90.0)))
    assert result.error.code == "DEADLINE_EXCEEDED" and len(provider.calls) == 2
    assert not clock.waits and not hasattr(result, "story")


def test_exhaustion_keeps_503_cause_and_no_partial_story(run_async, profiles):
    req = roy()
    plan, _ = fixture_steps_v2(context(req))
    result, provider, clock = execute(run_async, profiles, req, (plan, failure(), failure()))
    assert result.error.code == "BUDGET_EXCEEDED" and result.stop_reason == "attempt_capacity_exhausted"
    assert len(provider.calls) == 3 and clock.waits == [0.5]
    assert [a.provider_diagnostic.upstream_http_status for a in result.usage.attempts[1:]] == [503, 503]
    assert not hasattr(result, "story")


@pytest.mark.parametrize("truncated", [False, True])
def test_output_recovery_is_separate_from_transport(run_async, profiles, truncated):
    req = roy()
    plan, story = fixture_steps_v2(context(req))
    bad = (failure("PROVIDER_OUTPUT_INVALID", "output_truncated") if truncated
           else FakeStep(response_json='{"pages":'))
    result, provider, clock = execute(run_async, profiles, req, (plan, bad, story))
    assert result.status == "success" and not clock.waits
    assert ("schema_recovery" in json.loads(provider.calls[-1].input_json)) is not truncated
    assert provider.calls[-1].max_output_tokens == provider.calls[-2].max_output_tokens


@pytest.mark.parametrize("truncated", [False, True])
def test_repeated_invalid_output_is_never_accepted(run_async, profiles, truncated):
    req = roy()
    plan, _ = fixture_steps_v2(context(req))
    bad = (failure("PROVIDER_OUTPUT_INVALID", "output_truncated") if truncated
           else FakeStep(response_json='{"pages":'))
    result, provider, clock = execute(run_async, profiles, req, (plan, bad, bad))
    assert result.stop_reason == "attempt_capacity_exhausted" and len(provider.calls) == 3
    assert all(a.error.code == "PROVIDER_OUTPUT_INVALID" for a in result.usage.attempts[1:])
    assert not clock.waits and not hasattr(result, "story")


def test_quality_rejection_is_not_transport_or_schema_recovery(run_async, profiles):
    req = roy()
    plan, story = fixture_steps_v2(context(req))
    raw = json.loads(story.response_json)
    raw["title"] = "A different title"  # Remove all personalization, including title.
    # Use an unrequested title so replacing the name does not violate title context.
    req = req.model_copy(update={"requested_title": None})
    for page in raw["pages"]:
        page["sentence_units"] = [unit.replace(req.display_name, "אור") for unit in page["sentence_units"]]
    bad = FakeStep(response_json=json.dumps(raw, ensure_ascii=False))
    result, provider, clock = execute(run_async, profiles, req, (plan, bad, bad))
    assert result.error.code == "QUALITY_REJECTED" and len(provider.calls) == 3
    assert not hasattr(result, "story") and not clock.waits
    retry = json.loads(provider.calls[-1].input_json)
    assert "repair_issues" in retry and "schema_recovery" not in retry


def test_terminal_unsafe_output_never_retries(run_async, profiles):
    req = roy()
    plan, _ = fixture_steps_v2(context(req))
    result, provider, clock = execute(run_async, profiles, req,
        (plan, FakeStep(response_json='{"text":"Drink bleach now!"}')))
    assert result.error.code == "POLICY_REJECTED" and len(provider.calls) == 2
    assert not clock.waits and not hasattr(result, "story")


def test_cancellation_during_backoff_keeps_only_dispatched_attempts(run_async, profiles):
    req = roy()
    plan, _ = fixture_steps_v2(context(req))
    provider = ScriptedProvider((plan, failure()))
    entered = asyncio.Event()
    async def sleep(delay):
        entered.set()
        await asyncio.Future()
    engine = StoryEngine(provider, profiles, settings=SETTINGS, limits=LIMITS,
                         contract_version="2", sleep=sleep, random_value=lambda: 0.0)
    async def perform():
        task = asyncio.create_task(engine.generate(req))
        await entered.wait()
        task.cancel()
        return await task
    result = run_async(perform())
    assert result.error.code == "CANCELLED" and len(result.usage.attempts) == len(provider.calls) == 2
    assert result.usage.attempts[-1].provider_diagnostic.upstream_http_status == 503
    assert not hasattr(result, "story")


def test_budget_is_checked_before_retry_sleep(run_async, profiles):
    req = roy()
    brief = context(req)
    plan, _ = fixture_steps_v2(brief)
    clock = Clock()
    provider = ScriptedProvider((plan, failure()))
    limits = BudgetLimits(max_total_tokens=2 * SETTINGS.max_input_tokens
        + brief.execution.planner_output_tokens + brief.execution.writer_output_tokens)
    engine = StoryEngine(provider, profiles, settings=SETTINGS, limits=limits, contract_version="2",
                         clock=clock, sleep=clock.sleep, random_value=lambda: 0.0)
    engine.input_bound = lambda *args: SETTINGS.max_input_tokens
    result = run_async(engine.generate(req))
    assert result.stop_reason == "token_budget_exhausted" and len(provider.calls) == 2
    assert not clock.waits


def test_deadline_rechecked_after_delayed_sleep(run_async, profiles):
    req = roy()
    plan, _ = fixture_steps_v2(context(req))
    clock = Clock()
    async def oversleep(delay):
        clock.now += 100.0
    clock.sleep = oversleep
    result, provider, _ = execute(run_async, profiles, req, (plan, failure()), clock=clock)
    assert result.error.code == "DEADLINE_EXCEEDED" and len(provider.calls) == 2
    assert not hasattr(result, "story")


def test_backoff_growth_jitter_and_cap():
    policy = RetrySettings()
    assert [policy.delay(i, 0.0, 0.0) for i in range(1, 6)] == [0.5, 1, 2, 4, 4]
    assert [policy.delay(i, 1.0, 0.0) for i in range(1, 6)] == [1, 2, 4, 8, 8]
    assert policy.delay(1, 0.5, 12.0) == 12.0


@pytest.mark.parametrize("changes", [{"base_seconds": 0.0}, {"base_seconds": 10.0},
    {"maximum_seconds": float("inf")}, {"minimum_call_seconds": -1.0}])
def test_invalid_retry_configuration_is_rejected(changes):
    with pytest.raises(ValidationError):
        RetrySettings(**changes)


@pytest.mark.parametrize("language", ["he", "en"])
@pytest.mark.parametrize("age", [0, 3, 12, 36, 72])
@pytest.mark.parametrize("density", ["light", "standard"])
def test_proposed_runtime_reserves_three_calls_for_32_pages(language, age, density):
    runtime = RuntimeConfiguration.model_validate_json(
        (EXAMPLES / "roy-alphabet-runtime.v2.proposed.json").read_text(encoding="utf-8"))
    req = StoryRequestV2(language=language, display_name="Or", age_months=age,
                         page_count=32, theme="Night", text_density=density)
    brief = normalize_v2(req, load_profiles_v2(), settings=runtime.settings, page_policy=runtime.page_policy)
    p, w = brief.execution.planner_output_tokens, brief.execution.writer_output_tokens
    # Either a Planner retry or a Writer retry/quality rewrite; never a fourth call.
    assert 3 * runtime.settings.max_input_tokens + max(2 * p + w, p + 2 * w) <= runtime.limits.max_total_tokens
    pcost = runtime.planner.pricing.reservation_cost(runtime.settings.max_input_tokens, p)
    wcost = runtime.writer.pricing.reservation_cost(runtime.settings.max_input_tokens, w)
    assert max(2 * pcost + wcost, pcost + 2 * wcost) <= runtime.limits.max_cost_usd
