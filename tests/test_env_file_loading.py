import logging
from pathlib import Path

import uvicorn

from storyforge.api.configured import load_configuration
from storyforge.llm.configuration import GeminiConfig


def test_explicit_uvicorn_env_file_reaches_secret_configuration(tmp_path, monkeypatch, caplog):
    key = "offline-env-not-a-real-key"
    env_file = tmp_path / ".env"
    env_file.write_text(f'GEMINI_API_KEY="{key}"\nSTORYFORGE_ALLOW_PAID_CALLS=false\n', encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("STORYFORGE_ALLOW_PAID_CALLS", "false")
    caplog.set_level(logging.INFO)
    # Config construction loads the file; it never starts a server or provider.
    uvicorn.Config("storyforge.api.configured:create_configured_app", factory=True,
                   env_file=env_file, log_config=None, workers=1)
    import os
    assert os.environ["GEMINI_API_KEY"] == key
    assert os.environ["STORYFORGE_ALLOW_PAID_CALLS"] == "false"
    runtime, credentials = load_configuration({
        "STORYFORGE_CONFIG": str(Path(__file__).resolve().parents[1] / "docs/examples/gemini-smoke-runtime.json"),
        "STORYFORGE_ALLOW_PAID_CALLS": "true", "GEMINI_API_KEY": os.environ["GEMINI_API_KEY"],
    })
    assert isinstance(credentials, GeminiConfig)
    assert runtime.settings.max_attempts == 3 and runtime.limits.max_cost_usd == 0.015
    assert key not in repr(credentials) + credentials.model_dump_json() + caplog.text


def test_default_startup_never_discovers_dotenv(tmp_path, monkeypatch):
    import dotenv
    import os
    (tmp_path / ".env").write_text("GEMINI_API_KEY=offline-env-not-a-real-key\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    def forbidden(*args, **kwargs):
        raise AssertionError("Implicit dotenv discovery is forbidden")
    monkeypatch.setattr(dotenv, "load_dotenv", forbidden)
    uvicorn.Config("storyforge.api.app:create_app", factory=True, log_config=None, workers=1)
    assert "GEMINI_API_KEY" not in os.environ


def test_uvicorn_preserves_existing_process_key(tmp_path, monkeypatch):
    import os
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=offline-file-key\n", encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "offline-existing-process-key")
    uvicorn.Config("storyforge.api.configured:create_configured_app", factory=True,
                   env_file=env_file, log_config=None, workers=1)
    assert os.environ["GEMINI_API_KEY"] == "offline-existing-process-key"
