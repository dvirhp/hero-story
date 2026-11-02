import pytest
from pydantic import ValidationError

from storyforge.config import AppSettings
from storyforge.domain.story import Story, StoryPlan
from storyforge.llm.configuration import ModelCapabilities, OpenAIConfig
from storyforge.llm.schema import structured_schema


def test_explicit_model_and_secret_configuration():
    assert AppSettings().provider == "fake"
    assert AppSettings(provider="openai", model="offline-model").model == "offline-model"
    with pytest.raises(ValidationError):
        AppSettings(provider="openai")
    config = OpenAIConfig(api_key="offline-test-not-a-real-key", timeout_seconds=30.0)
    assert "offline-test" not in repr(config)
    assert "api_key" not in config.model_dump()


@pytest.mark.parametrize("model", [StoryPlan, Story])
def test_strict_structural_schema_keeps_local_validation_separate(model):
    schema = structured_schema(model)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    for definition in schema.get("$defs", {}).values():
        if definition.get("type") == "object":
            assert set(definition["required"]) == set(definition["properties"])
    assert "minLength" not in str(schema)
    assert "default" not in str(schema)
    assert "minLength" in str(model.model_json_schema())


def test_capabilities_have_no_invented_defaults():
    with pytest.raises(ValidationError):
        ModelCapabilities(model="offline-model")
