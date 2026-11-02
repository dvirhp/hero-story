import pytest
from pydantic import ValidationError

from storyforge.orchestration.budget import BudgetLimits, FakePricing, input_token_bound
from storyforge.orchestration.state import RunState
from storyforge.prompts.builders import build_request
from storyforge.domain.generation import TokenUsage
from storyforge.domain.story import StoryPlan


def test_reservations_are_versioned_synthetic_and_unknown_is_not_zero():
    pricing = FakePricing(version="synthetic-test-v1", input_usd_per_million=1.0, output_usd_per_million=2.0)
    assert pricing.cost(1000, 500) == 0.002
    assert pricing.usage_cost(TokenUsage(source="unknown")) is None
    assert FakePricing().version == "fake-zero-v1"
    with pytest.raises(ValidationError):
        BudgetLimits(max_total_tokens=0)


@pytest.mark.parametrize("language", ["he", "en"])
def test_profile_and_user_data_are_separate_from_instructions(make_brief, language):
    brief = make_brief(0, language)
    request = build_request("planner", brief, "scripted-v1", 1200, 30.0)
    assert brief.request.display_name not in request.instructions
    assert brief.request.display_name in request.input_json
    assert "plot-free" in request.instructions
    assert input_token_bound(request, StoryPlan, 256) > len(request.input_json)


def test_state_rejects_false_success_and_lost_reservations():
    args = dict(request_id="r1", raw_input=None, started_at=0.0, deadline=90.0,
                remaining_seconds=90.0, remaining_tokens=33000, remaining_cost_usd=0.0, versions=())
    state = RunState(**args)
    with pytest.raises(ValidationError):
        state.updated(status="success")
    with pytest.raises(ValidationError):
        state.updated(attempts_used=1)
