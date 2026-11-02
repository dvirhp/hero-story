import pytest
from pydantic import ValidationError

from storyforge.domain.generation import TokenUsage
from storyforge.orchestration.budget import ModelPricing


def test_cached_and_reasoning_are_subsets_not_added_twice():
    pricing = ModelPricing(model="offline-model", version="synthetic-v1",
                           reservation_input_usd_per_million=2.0, reservation_output_usd_per_million=4.0,
                           input_usd_per_million=2.0, output_usd_per_million=4.0, cached_input_usd_per_million=1.0)
    usage = TokenUsage(source="reported", input_tokens=100, output_tokens=50, cached_input_tokens=20, reasoning_output_tokens=10)
    assert pricing.usage_cost(usage) == pytest.approx(0.00038)
    assert pricing.reservation_cost(100, 50) == pytest.approx(0.0004)


def test_unknown_prices_are_not_free():
    pricing = ModelPricing(model="offline-model", version="unknown-v1",
                           reservation_input_usd_per_million=1.0, reservation_output_usd_per_million=2.0)
    assert pricing.usage_cost(TokenUsage(source="reported", input_tokens=100, output_tokens=50)) is None
    assert pricing.reservation_cost(100, 50) > 0


def test_reservation_rates_cover_known_prices():
    with pytest.raises(ValidationError):
        ModelPricing(model="offline-model", version="bad-v1", reservation_input_usd_per_million=1.0,
                     reservation_output_usd_per_million=2.0, input_usd_per_million=2.0)
