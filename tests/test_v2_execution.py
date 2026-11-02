"""Offline v2 acceptance, recovery and API migration contracts."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from storyforge.api.app import create_app
from storyforge.api.dependencies import Resources
from storyforge.config import AppSettings
from storyforge.development.v2 import load_profiles_v2
from storyforge.domain.generation import GenerationError
from storyforge.domain.story_v2 import StoryPlanV2, StoryRequestV2, StoryV2
from storyforge.llm.fake import FakeProvider, FakeStep
from storyforge.llm.fixtures import LocalFixtureProvider
from storyforge.llm.fixtures_v2 import fixture_steps_v2
from storyforge.orchestration.budget import BudgetLimits
from storyforge.orchestration.engine import StoryEngine
from storyforge.quality.gate import assess_story
from storyforge.validation.normalization_v2 import normalize_v2
from storyforge.validation.page_policy import PagePolicy

SETTINGS = AppSettings(planner_output_tokens=5000, writer_output_tokens=20000, max_input_tokens=64000)
LIMITS = BudgetLimits(max_total_tokens=260000)
EXAMPLES = Path(__file__).resolve().parents[1] / "docs" / "examples"


def request(language="en", age=0, pages=4, **changes):
    return StoryRequestV2(language=language, display_name="אור" if language == "he" else "Or",
                          age_months=age, page_count=pages, theme="לילה" if language == "he" else "Night", **changes)


def brief(req):
    return normalize_v2(req, load_profiles_v2(), settings=SETTINGS)


def engine(profiles, provider=None, **changes):
    return StoryEngine(provider if provider is not None else LocalFixtureProvider(), profiles,
                       settings=changes.pop("settings", SETTINGS), limits=changes.pop("limits", LIMITS),
                       contract_version="2", **changes)


@pytest.mark.parametrize("language", ["he", "en"])
@pytest.mark.parametrize("age", [0, 3, 12, 36, 72, 10000])
@pytest.mark.parametrize("pages", [1, 6, 27, 32])
def test_graph_keeps_exact_user_length_for_every_age(run_async, profiles, language, age, pages):
    req = request(language, age, pages)
    result = run_async(engine(profiles).generate(req))
    assert result.status == "success", result
    assert result.story.page_count == len(result.story.pages) == pages
    assert result.story.schema_version == "2"
    assert result.quality.passed and len(result.usage.attempts) == 2
    assert result.story.validate_for(brief(req)) is result.story


@pytest.mark.parametrize("kind", ["general", "bedtime", "adventure", "educational"])
def test_story_types_share_one_graph(run_async, profiles, kind):
    assert run_async(engine(profiles).generate(request(story_type=kind))).status == "success"


def test_roy_27_letter_book_acceptance_through_http(run_async, profiles):
    req = StoryRequestV2.model_validate_json((EXAMPLES / "roy-alphabet-request.v2.he.json").read_text(encoding="utf-8"))
    assert "".join(t.label for t in req.structure.targets) == "אבגדהוזחטיכלמנסעפצקרשתךםןףץ"
    provider = LocalFixtureProvider()
    app = create_app(resources=Resources(profiles=profiles, settings=SETTINGS, limits=LIMITS, provider=provider))
    async def perform():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                return await client.post("/v2/stories/generate", json=req.model_dump(mode="json"))
    response = run_async(perform())
    assert response.status_code == 200, response.text
    story = StoryV2.model_validate_json(json.dumps(response.json()["story"]))
    assert story.page_count == 27 and story.title == req.requested_title
    assert story.validate_for(brief(req)) is story
    for target, page in zip(req.structure.targets, story.pages, strict=True):
        assert page.target_id == target.target_id and target.label in page.text
        assert 2 <= len(page.sentence_units) <= 3
        assert 12 <= len(page.text.split()) <= 24
        assert req.display_name in page.text
        if target.base_form:
            assert target.base_form in page.text and target.example_word in page.text
    assert any(i["code"] == "NARRATIVE_COVERAGE_REVIEW" for i in response.json()["quality"]["issues"])
    # Synthetic fixtures prove structure, not final-form teaching, fluency or hero agency.


def test_generic_educational_targets_are_not_alphabet_specific(run_async, profiles):
    raw = request(pages=2, age=36, story_type="educational").model_dump(mode="json")
    raw["structure"] = {"targets": [{"target_id": "red", "label": "red"}, {"target_id": "blue", "label": "blue"}]}
    result = run_async(engine(profiles).generate(raw))
    assert result.status == "success"
    assert [p.target_id for p in result.story.pages] == ["red", "blue"]


@pytest.mark.parametrize("mutation", ["short", "order", "duplicate_id", "number", "wrong_title", "missing_label", "units"])
def test_quality_rejects_invalid_page_structure(mutation):
    req = StoryRequestV2.model_validate_json((EXAMPLES / "roy-alphabet-request.v2.he.json").read_text(encoding="utf-8"))
    context = brief(req)
    raw = json.loads(fixture_steps_v2(context)[1].response_json)
    if mutation == "short":
        raw["pages"].pop(); raw["page_count"] -= 1
    elif mutation == "order":
        raw["pages"][0]["target_id"], raw["pages"][1]["target_id"] = raw["pages"][1]["target_id"], raw["pages"][0]["target_id"]
    elif mutation == "duplicate_id":
        raw["pages"][1]["page_id"] = raw["pages"][0]["page_id"]
    elif mutation == "number":
        raw["pages"][0]["page_number"] = 2
    elif mutation == "wrong_title":
        raw["title"] = "Another title"
    elif mutation == "missing_label":
        raw["pages"][0]["sentence_units"] = [s.replace("א", "ב") for s in raw["pages"][0]["sentence_units"]]
    else:
        raw["pages"][0]["sentence_units"] = [" ".join(raw["pages"][0]["sentence_units"])]
    report = assess_story(raw, context)
    assert not report.passed


@pytest.mark.parametrize("stage", ["planner", "writer"])
def test_incomplete_book_recovers_without_truncation(run_async, profiles, stage):
    req = request(pages=6)
    plan, story = fixture_steps_v2(brief(req))
    source = plan if stage == "planner" else story
    raw = json.loads(source.response_json)
    raw["pages"].pop(); raw["page_count"] -= 1
    bad = FakeStep(response_json=json.dumps(raw))
    steps = (bad, plan, story) if stage == "planner" else (plan, bad, story)
    provider = FakeProvider(steps)
    result = run_async(engine(profiles, provider).generate(req))
    assert result.status == "success" and result.story.page_count == 6
    assert len(provider.calls) == 3
    assert json.loads(provider.calls[-1].input_json)["brief"]["request"]["page_count"] == 6


def test_quality_rewrite_is_shared_third_attempt(run_async, profiles):
    req = request()
    plan, story = fixture_steps_v2(brief(req))
    raw = json.loads(story.response_json)
    for page in raw["pages"]:
        page["sentence_units"] = [unit.replace("Or", "Someone") for unit in page["sentence_units"]]
    provider = FakeProvider((plan, FakeStep(response_json=json.dumps(raw)), story))
    result = run_async(engine(profiles, provider).generate(req))
    assert result.status == "success" and len(provider.calls) == 3
    assert "repair_issues" in json.loads(provider.calls[-1].input_json)


@pytest.mark.parametrize("failure", ["refusal", "malformed", "unsafe", "timeout"])
def test_failures_remain_bounded_and_sanitized(run_async, profiles, failure):
    if failure == "refusal":
        step = FakeStep(error=GenerationError(code="PROVIDER_REFUSED", stage="planner", retryable=False, message="private"))
    elif failure == "unsafe":
        step = FakeStep(response_json='{"text":"Drink bleach now!"}')
    elif failure == "timeout":
        step = FakeStep(latency_seconds=1000.0, response_json="{}")
    else:
        step = FakeStep(response_json="{}")
    provider = FakeProvider((step, step, step))
    result = run_async(engine(profiles, provider).generate(request()))
    assert result.status == "failure" and len(provider.calls) <= 3
    assert "private" not in result.model_dump_json() and not hasattr(result, "story")


@pytest.mark.parametrize("case", ["page_limit", "output_limit", "total_tokens", "input_limit"])
def test_admission_fails_before_provider_without_clamping(run_async, profiles, case):
    provider = FakeProvider(())
    changes = {}
    req = request(pages=33 if case == "page_limit" else 27)
    if case == "output_limit": changes["settings"] = AppSettings()
    elif case == "total_tokens": changes["limits"] = BudgetLimits(max_total_tokens=1)
    elif case == "input_limit": changes["settings"] = SETTINGS.model_copy(update={"max_input_tokens": 1})
    result = run_async(engine(profiles, provider, **changes).generate(req))
    assert result.status == "failure" and not provider.calls
    assert req.page_count == (33 if case == "page_limit" else 27)


def test_configurable_page_bounds_allow_more_without_graph_changes(run_async, profiles):
    result = run_async(engine(profiles, page_policy=PagePolicy(maximum_pages=40)).generate(request(pages=40)))
    assert result.status == "success" and len(result.story.pages) == 40


def test_http_v1_deprecated_and_v2_requires_count(run_async):
    app = create_app()
    async def perform():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                payload = dict(language="en", display_name="Or", age_months=0, theme="Night")
                v1 = await client.post("/v1/stories/generate", json=payload)
                v2 = await client.post("/v2/stories/generate", json=payload)
                explicit = await client.post("/v2/stories/generate", json={**payload, "page_count": 1})
                return v1, v2, explicit
    v1, v2, explicit = run_async(perform())
    assert v1.status_code == 200 and len(v1.json()["story"]["pages"]) == 4
    assert v2.status_code == 422 and not v2.json()["usage"]["attempts"]
    assert explicit.status_code == 200 and explicit.json()["story"]["page_count"] == 1
    assert app.openapi()["paths"]["/v1/stories/generate"]["post"]["deprecated"]
    assert "page_count" in app.openapi()["components"]["schemas"]["StoryRequestV2"]["required"]


def test_v2_cancellation_retains_attempt_ledger(run_async, profiles):
    async def perform():
        entered = asyncio.Event()
        class WaitingProvider:
            async def generate(self, request, schema):
                entered.set()
                await asyncio.Future()
        task = asyncio.create_task(engine(profiles, WaitingProvider()).generate(request()))
        await asyncio.wait_for(entered.wait(), timeout=5)
        task.cancel()
        return await task
    result = run_async(perform())
    assert result.error.code == "CANCELLED" and len(result.usage.attempts) == 1
    assert result.usage.has_unknown_usage


def test_repetition_is_advisory_even_when_entire_pages_repeat():
    req = request(pages=6)
    report = assess_story(fixture_steps_v2(brief(req))[1].response_json, brief(req))
    assert report.passed
    assert any(i.code == "FORMULAIC_PAGE_REPETITION" and i.severity == "advisory" for i in report.issues)
