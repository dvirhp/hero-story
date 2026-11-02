import asyncio
import json

import pytest

from storyforge.config import AppSettings
from storyforge.domain.generation import GenerationError, TokenUsage
from storyforge.domain.story import PageIntent, PlotElements, StoryPlan, StoryRequest
from storyforge.llm.fake import FakeProvider, FakeStep
from storyforge.orchestration.budget import BudgetLimits, FakePricing
from storyforge.orchestration.engine import StoryEngine
from storyforge.validation.normalization import normalize_request


@pytest.fixture
def scenario(profiles):
    def make(language="en", age=0):
        request = StoryRequest(language=language, display_name="אור" if language == "he" else "Or",
                               age_months=age, theme="לילה" if language == "he" else "Night")
        brief = normalize_request(request, profiles)
        p = brief.profile
        plan = StoryPlan(
            language=language, title_concept="Night", protagonist=request.display_name,
            strategy=p.requirements.strategy,
            plot=PlotElements(goal="A goal", obstacle_or_choices="A choice", resolution="Home")
                 if p.requirements.strategy in ("simple_goal", "connected_scenes") else None,
            pages=tuple(PageIntent(page_number=i, intent="A gentle moment")
                        for i in range(1, p.requirements.hard.page_count + 1)),
        )
        word = "שלום" if language == "he" else "soft"
        story = dict(title="לילה" if language == "he" else "Night", language=language,
                     direction="rtl" if language == "he" else "ltr", profile_id=p.band_id, profile_version=p.version,
                     pages=[dict(page_id=f"p{i}", page_number=i,
                                 text=" ".join([request.display_name] + [word] * (p.requirements.hard.words_per_page.minimum - 1)))
                            for i in range(1, p.requirements.hard.page_count + 1)])
        return request, plan.model_dump_json(), json.dumps(story, ensure_ascii=False)
    return make


def scripted(plan, story, **kwargs):
    return FakeProvider((FakeStep(response_json=plan, **kwargs), FakeStep(response_json=story, **kwargs)))


@pytest.mark.parametrize("language", ["en", "he"])
@pytest.mark.parametrize("age", [0, 6, 24, 48, 180])
def test_success_and_four_explicit_nodes(profiles, scenario, run_async, language, age):
    request, plan, story = scenario(language, age)
    provider = scripted(plan, story)
    engine = StoryEngine(provider, profiles)
    result = run_async(engine.generate(request, request_id="r1"))
    assert result.status == "success", result
    assert len(provider.calls) == 2
    assert result.story.language == language
    assert result.story.profile_version == profiles.version
    assert result.quality.passed
    assert len(result.usage.attempts) == 2
    assert result.usage.has_unknown_usage
    assert all(a.estimated_cost_usd is None for a in result.usage.attempts)
    assert set(engine.graph.get_graph().nodes) == {
        "__start__", "input_validation", "story_planner", "story_writer", "quality_gate", "__end__"}


@pytest.mark.parametrize("raw_input", [{}, {"language": "en", "age_months": -1}, None, "bad json"])
def test_invalid_input_zero_calls(profiles, run_async, raw_input):
    provider = FakeProvider(())
    result = run_async(StoryEngine(provider, profiles).generate(raw_input))
    assert result.status == "failure"
    assert result.error.code == "INPUT_INVALID"
    assert result.usage.attempts == ()
    assert not provider.calls


@pytest.mark.parametrize("stage", ["planner", "writer"])
def test_schema_recovery_uses_one_shared_extra_slot(profiles, scenario, run_async, stage):
    request, plan, story = scenario()
    payloads = ("{}", plan, story) if stage == "planner" else (plan, "{}", story)
    provider = FakeProvider(tuple(FakeStep(response_json=p) for p in payloads))
    result = run_async(StoryEngine(provider, profiles).generate(request))
    assert result.status == "success", result
    assert len(provider.calls) == 3
    assert result.usage.attempts[0 if stage == "planner" else 1].outcome == "failure"
    assert "schema_recovery" in provider.calls[1 if stage == "planner" else 2].input_json


def test_planner_retry_preserves_writer_slot(profiles, scenario, run_async):
    request, _, _ = scenario()
    provider = FakeProvider((FakeStep(response_json="{}"), FakeStep(response_json="{}"), FakeStep(response_json="{}")))
    result = run_async(StoryEngine(provider, profiles).generate(request))
    assert result.error.code == "BUDGET_EXCEEDED"
    assert len(provider.calls) == 2
    assert all(a.stage == "planner" for a in result.usage.attempts)


def test_writer_failures_never_exceed_three_calls(profiles, scenario, run_async):
    request, plan, _ = scenario()
    provider = FakeProvider(tuple(FakeStep(response_json=p) for p in (plan, "{}", "{}", "{}")))
    result = run_async(StoryEngine(provider, profiles).generate(request))
    assert result.status == "failure"
    assert result.error.code == "BUDGET_EXCEEDED"
    assert len(provider.calls) == 3
    assert "story" not in result.model_dump()


@pytest.mark.parametrize("code,retryable,success", [
    ("PROVIDER_UNAVAILABLE", True, True), ("PROVIDER_REFUSED", False, False),
    ("CONFIGURATION_ERROR", False, False), ("POLICY_REJECTED", True, False),
])
def test_provider_failure_routing_and_sanitization(profiles, scenario, run_async, code, retryable, success):
    request, plan, story = scenario()
    step = FakeStep(error=GenerationError(code=code, stage="planner", retryable=retryable, message="Sensitive provider diagnostic"))
    provider = FakeProvider((step, FakeStep(response_json=plan), FakeStep(response_json=story)))
    result = run_async(StoryEngine(provider, profiles).generate(request))
    assert (result.status == "success") == success
    assert len(provider.calls) == (3 if success else 1)
    assert "Sensitive" not in result.model_dump_json()


@pytest.mark.parametrize("repair_succeeds", [True, False])
def test_quality_rewrite(profiles, scenario, run_async, repair_succeeds):
    request, plan, story = scenario()
    broken = story.replace('Or', 'Someone')
    provider = FakeProvider(tuple(FakeStep(response_json=p) for p in (plan, broken, story if repair_succeeds else broken)))
    result = run_async(StoryEngine(provider, profiles).generate(request))
    assert (result.status == "success") == repair_succeeds
    assert len(provider.calls) == 3
    repair = json.loads(provider.calls[-1].input_json)
    assert repair["repair_issues"][0]["code"] == "PERSONALIZATION_MISSING"
    assert "previous_draft" in repair and "plan" in repair
    if not repair_succeeds:
        assert result.error.code == "QUALITY_REJECTED"
        assert "story" not in result.model_dump()


@pytest.mark.parametrize("malformed", [True, False])
@pytest.mark.parametrize("unsafe", ["Drink bleach now!", "hidden\u202e"])
def test_unsafe_output_terminal_before_schema_repair(profiles, scenario, run_async, malformed, unsafe):
    request, plan, story = scenario()
    raw = json.loads(story)
    raw["pages"][0]["text"] = unsafe
    if malformed:
        raw.pop("title")
    provider = FakeProvider((FakeStep(response_json=plan), FakeStep(response_json=json.dumps(raw)), FakeStep(response_json=story)))
    result = run_async(StoryEngine(provider, profiles).generate(request))
    assert result.status == "failure"
    assert result.error.code == "POLICY_REJECTED"
    assert len(provider.calls) == 2
    assert result.quality and any(i.severity == "terminal" for i in result.quality.issues)
    assert unsafe not in result.model_dump_json()


def test_unknown_usage_retains_positive_conservative_reservation(profiles, scenario, run_async):
    request, plan, story = scenario()
    pricing = FakePricing(version="synthetic-test-v1", input_usd_per_million=1.0, output_usd_per_million=2.0)
    provider = scripted(plan, story)
    result = run_async(StoryEngine(provider, profiles, pricing=pricing,
                                  limits=BudgetLimits(max_cost_usd=1.0)).generate(request))
    assert result.status == "success"
    assert result.usage.known_estimated_cost_usd == 0.0
    assert result.usage.has_unknown_usage
    assert result.usage.upper_estimated_cost_usd > 0
    assert all(a.usage.input_tokens is None and a.estimated_cost_usd is None for a in result.usage.attempts)


@pytest.mark.parametrize("limit", ["input", "total", "cost"])
def test_preflight_budgets_make_zero_calls(profiles, scenario, run_async, limit):
    request, plan, story = scenario()
    provider = scripted(plan, story)
    settings = AppSettings(max_input_tokens=1) if limit == "input" else AppSettings()
    limits = BudgetLimits(max_total_tokens=1) if limit == "total" else BudgetLimits()
    pricing = FakePricing(input_usd_per_million=1.0) if limit == "cost" else FakePricing()
    result = run_async(StoryEngine(provider, profiles, settings=settings, limits=limits, pricing=pricing).generate(request))
    assert result.error.code == "BUDGET_EXCEEDED"
    assert not provider.calls


def test_known_usage_and_caps(profiles, scenario, run_async):
    request, plan, story = scenario()
    usage = TokenUsage(source="reported", input_tokens=100, output_tokens=50)
    pricing = FakePricing(input_usd_per_million=1.0, output_usd_per_million=2.0)
    result = run_async(StoryEngine(scripted(plan, story, usage=usage), profiles, pricing=pricing,
                                  limits=BudgetLimits(max_cost_usd=1.0)).generate(request))
    assert result.status == "success"
    assert result.usage.known_estimated_cost_usd == pytest.approx(0.0004)
    assert not result.usage.has_unknown_usage
    provider = scripted(plan, story, usage=TokenUsage(source="reported", input_tokens=100, output_tokens=1201))
    result = run_async(StoryEngine(provider, profiles).generate(request))
    assert result.error.code == "BUDGET_EXCEEDED"
    assert len(provider.calls) == 1


def test_virtual_deadline_counts_fake_latency(profiles, scenario, run_async):
    request, plan, story = scenario()
    provider = scripted(plan, story, latency_seconds=1.0)
    settings = AppSettings(attempt_timeout_seconds=1.0, request_timeout_seconds=2.0)
    result = run_async(StoryEngine(provider, profiles, settings=settings, clock=lambda: 0.0).generate(request))
    assert result.error.code == "DEADLINE_EXCEEDED"
    assert len(provider.calls) == 2
    assert result.total_latency_seconds == 2.0


def test_cancellation_preserves_attempt_and_sanitized_failure(profiles, scenario, run_async):
    request, _, _ = scenario()
    entered = asyncio.Event()
    class WaitingProvider:
        async def generate(self, request, output_schema):
            entered.set()
            await asyncio.Future()
    engine = StoryEngine(WaitingProvider(), profiles)
    async def cancel():
        task = asyncio.create_task(engine.generate(request))
        await entered.wait()
        task.cancel()
        return await task
    result = run_async(cancel())
    assert result.status == "failure"
    assert result.error.code == "CANCELLED"
    assert len(result.usage.attempts) == 1
    assert result.usage.has_unknown_usage
    assert result.usage.attempts[0].outcome == "failure"


def test_actual_async_timeout_is_bounded(profiles, scenario, run_async):
    request, _, _ = scenario()
    class WaitingProvider:
        async def generate(self, request, output_schema):
            await asyncio.Future()
    settings = AppSettings(attempt_timeout_seconds=0.01, request_timeout_seconds=0.01)
    result = run_async(StoryEngine(WaitingProvider(), profiles, settings=settings).generate(request))
    assert result.error.code == "DEADLINE_EXCEEDED"
    assert len(result.usage.attempts) == 1


def test_transport_exception_retry_is_sanitized(profiles, scenario, run_async):
    request, plan, story = scenario()
    class FlakyProvider(FakeProvider):
        first = True
        async def generate(self, request, output_schema):
            if self.first:
                self.first = False
                raise ConnectionError("private transport secret")
            return await super().generate(request, output_schema)
    provider = FlakyProvider((FakeStep(response_json=plan), FakeStep(response_json=story)))
    result = run_async(StoryEngine(provider, profiles).generate(request))
    assert result.status == "success"
    assert len(result.usage.attempts) == 3
    assert "private transport" not in result.usage.model_dump_json()


def test_deterministic_routing_and_immutable_snapshot(profiles, scenario, run_async):
    request, plan, story = scenario()
    async def run():
        engine = StoryEngine(scripted(plan, story), profiles, clock=lambda: 0.0)
        states = []
        original = engine._publish
        def capture(run, session):
            states.append(run)
            return original(run, session)
        engine._publish = capture
        result = await engine.generate(request, request_id="fixed")
        return result, states
    first, states = run_async(run())
    second, _ = run_async(run())
    assert first == second
    assert [s.stage for s in states] == ["validation", "planner", "writer", "quality"]
    assert states[-1].status == "success"
    assert states[-1].attempts_used == 2
    assert all(s.brief.profile == states[0].brief.profile for s in states)


def test_environment_tracing_is_disabled(profiles, scenario, run_async, monkeypatch, caplog):
    request, plan, story = scenario()
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    result = run_async(StoryEngine(scripted(plan, story), profiles).generate(request))
    assert result.status == "success"
    assert not caplog.records


@pytest.mark.parametrize("language,age", [("en", 0), ("he", 180)])
def test_local_demo_is_offline_and_prints_no_story(run_async, language, age):
    from storyforge.demo import run_demo
    result = run_async(run_demo(language, age))
    assert result["status"] == "success"
    assert result["attempts"] == 2
    assert "story" not in result


def test_two_slot_setting_does_not_retry_planner(profiles, scenario, run_async):
    request, plan, story = scenario()
    provider = FakeProvider(tuple(FakeStep(response_json=p) for p in ("{}", plan, story)))
    settings = AppSettings(max_attempts=2, max_quality_rewrites=0)
    result = run_async(StoryEngine(provider, profiles, settings=settings).generate(request))
    assert result.error.code == "BUDGET_EXCEEDED"
    assert len(provider.calls) == 1


def test_retry_then_quality_failure_cannot_get_a_fourth_call(profiles, scenario, run_async):
    request, plan, story = scenario()
    provider = FakeProvider(tuple(FakeStep(response_json=p) for p in ("{}", plan, story.replace('Or', 'Someone'), story)))
    result = run_async(StoryEngine(provider, profiles).generate(request))
    assert result.error.code == "QUALITY_REJECTED"
    assert len(provider.calls) == 3


def test_rewrite_preserves_page_ids(profiles, scenario, run_async):
    request, plan, story = scenario()
    changed_ids = json.loads(story)
    changed_ids["pages"][0]["page_id"] = "changed"
    provider = FakeProvider(tuple(FakeStep(response_json=p) for p in (
        plan, story.replace('Or', 'Someone'), json.dumps(changed_ids))))
    result = run_async(StoryEngine(provider, profiles).generate(request))
    assert result.status == "failure"
    assert len(provider.calls) == 3
    assert result.usage.attempts[-1].error.code == "PROVIDER_OUTPUT_INVALID"


def test_profile_snapshot_survives_configuration_change_mid_run(profiles, scenario, run_async):
    from storyforge.development.models import DevelopmentConfig
    request, plan, story = scenario()
    data = profiles.model_dump(mode="json")
    data["version"] = "future-v2"
    newer = DevelopmentConfig.model_validate_json(json.dumps(data))
    class ChangingProvider(FakeProvider):
        async def generate(self, request, output_schema):
            engine.profiles = newer
            return await super().generate(request, output_schema)
    engine = StoryEngine(ChangingProvider((FakeStep(response_json=plan), FakeStep(response_json=story))), profiles)
    result = run_async(engine.generate(request))
    assert result.status == "success"
    assert result.story.profile_version == profiles.version


def test_sequential_calls_have_isolated_ledgers(profiles, scenario, run_async):
    request, plan, story = scenario()
    provider = FakeProvider(tuple(FakeStep(response_json=p) for p in (plan, story, plan, story)))
    engine = StoryEngine(provider, profiles)
    first = run_async(engine.generate(request, request_id="first"))
    second = run_async(engine.generate(request, request_id="second"))
    assert first.status == second.status == "success"
    assert [a.attempt_number for a in first.usage.attempts] == [1, 2]
    assert [a.attempt_number for a in second.usage.attempts] == [1, 2]


def test_per_attempt_timeout_recovers_when_overall_time_remains(profiles, scenario, run_async):
    request, plan, story = scenario()
    provider = FakeProvider((FakeStep(response_json=plan, latency_seconds=31.0),
                             FakeStep(response_json=plan), FakeStep(response_json=story)))
    result = run_async(StoryEngine(provider, profiles, clock=lambda: 0.0).generate(request))
    assert result.status == "success"
    assert len(provider.calls) == 3
    assert result.total_latency_seconds == 30.0
    assert result.usage.attempts[0].error.code == "DEADLINE_EXCEEDED"


def test_deadline_before_first_node_has_zero_calls(profiles, scenario, run_async):
    request, plan, story = scenario()
    times = iter((0.0, 100.0))
    def clock():
        return next(times, 100.0)
    provider = scripted(plan, story)
    result = run_async(StoryEngine(provider, profiles, clock=clock).generate(request))
    assert result.error.code == "DEADLINE_EXCEEDED"
    assert not provider.calls


def test_unexpected_provider_exception_is_terminal_and_sanitized(profiles, scenario, run_async):
    request, _, _ = scenario()
    class BrokenProvider:
        async def generate(self, request, output_schema):
            raise RuntimeError("private API diagnostic")
    result = run_async(StoryEngine(BrokenProvider(), profiles).generate(request))
    assert result.error.code == "CONFIGURATION_ERROR"
    assert len(result.usage.attempts) == 1
    assert "private API diagnostic" not in result.model_dump_json()


def test_input_policy_rejection_zero_provider_calls(profiles, scenario, run_async):
    request, plan, story = scenario()
    raw = request.model_dump(mode="json")
    raw["guidance"] = "Drink bleach now!"
    provider = scripted(plan, story)
    result = run_async(StoryEngine(provider, profiles).generate(raw))
    assert result.error.code == "POLICY_REJECTED"
    assert not provider.calls


@pytest.mark.parametrize("stage", ["planner", "writer"])
def test_profile_context_mismatch_recovery(profiles, scenario, run_async, stage):
    request, plan, story = scenario()
    bad = json.loads(plan if stage == "planner" else story)
    if stage == "planner":
        bad["protagonist"] = "Different"
    else:
        bad["profile_version"] = "Different"
    script = (json.dumps(bad), plan, story) if stage == "planner" else (plan, json.dumps(bad), story)
    provider = FakeProvider(tuple(FakeStep(response_json=p) for p in script))
    result = run_async(StoryEngine(provider, profiles).generate(request))
    assert result.status == "success"
    assert len(provider.calls) == 3


def test_custom_safety_rules_survive_adapter_schema_rejection(profiles, scenario, run_async):
    from storyforge.quality.rules import QualityRules
    rules = QualityRules(version="custom-v1", rubric_version="custom-language-v1",
                         prohibited_directives=("Custom banned sentence",))
    request, plan, story = scenario()
    bad = json.loads(story)
    bad.pop("title")
    bad["pages"][0]["text"] = "Custom banned sentence."
    provider = FakeProvider((FakeStep(response_json=plan), FakeStep(response_json=json.dumps(bad))), rules=rules)
    result = run_async(StoryEngine(provider, profiles, rules=rules).generate(request))
    assert result.error.code == "POLICY_REJECTED"
    assert result.quality.check_version == rules.version
    assert len(provider.calls) == 2


def test_concurrent_runs_have_no_shared_state(profiles, scenario, run_async):
    en, en_plan, en_story = scenario("en", 0)
    he, he_plan, he_story = scenario("he", 180)
    class RoutingFake:
        calls = 0
        async def generate(self, request, output_schema):
            self.calls += 1
            await asyncio.sleep(0)
            lang = json.loads(request.input_json)["brief"]["request"]["language"]
            raw = {("en", "planner"): en_plan, ("en", "writer"): en_story,
                   ("he", "planner"): he_plan, ("he", "writer"): he_story}[(lang, request.stage)]
            return await FakeProvider((FakeStep(response_json=raw),)).generate(request, output_schema)
    provider = RoutingFake()
    engine = StoryEngine(provider, profiles)
    async def both():
        return await asyncio.gather(engine.generate(en, request_id="en"), engine.generate(he, request_id="he"))
    results = run_async(both())
    assert provider.calls == 4
    assert [result.story.language for result in results] == ["en", "he"]
    assert all(len(result.usage.attempts) == 2 for result in results)
