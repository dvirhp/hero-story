import pytest
from pydantic import ValidationError

from storyforge.config import AppSettings


def test_safe_defaults(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "unused-test-sentinel")
    settings = AppSettings()
    assert settings.provider == "fake"
    assert settings.max_attempts == 3
    assert "unused-test-sentinel" not in settings.model_dump_json()


@pytest.mark.parametrize("change", [
    {"provider": "real"}, {"model": "paid-model"}, {"api_key": "secret"},
    {"max_attempts": 4}, {"max_attempts": True}, {"max_attempts": 1},
    {"max_attempts": 2}, {"max_quality_rewrites": 2}, {"max_input_tokens": 0},
    {"attempt_timeout_seconds": 100.0}, {"request_timeout_seconds": float("inf")},
    {"request_timeout_seconds": float("nan")},
])
def test_settings_reject_invalid_limits(change):
    with pytest.raises(ValidationError):
        AppSettings(**change)


def test_two_call_configuration():
    assert AppSettings(max_attempts=2, max_quality_rewrites=0).max_attempts == 2
