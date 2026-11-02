"""Load packaged, versioned product hypotheses explicitly (no import-time I/O)."""

from importlib.resources import files

from storyforge.development.models import DevelopmentConfig


def load_default_profiles() -> DevelopmentConfig:
    data = files("storyforge.development").joinpath("profiles.v1.json").read_text(encoding="utf-8")
    return DevelopmentConfig.model_validate_json(data)
