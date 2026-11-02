"""Versioned, configurable heuristics. None establishes fluency or safety."""

from typing import Annotated

from pydantic import Field, model_validator

from storyforge.domain.base import Contract, Label, Language, PositiveInt


class ScriptRule(Contract):
    language: Language
    minimum_target_ratio: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)] = 0.8
    minimum_letters: PositiveInt = 20


class QualityRules(Contract):
    version: Label = "quality-v1"
    rubric_version: Label = "language-v1"
    scripts: tuple[ScriptRule, ...] = (ScriptRule(language="en"), ScriptRule(language="he"))
    # Whole-sentence directive matches only, not a general keyword blocklist.
    prohibited_directives: tuple[Label, ...] = (
        "drink bleach now", "you should drink bleach", "mix bleach and ammonia",
        "שתה אקונומיקה עכשיו", "עליך לשתות אקונומיקה", "ערבב אקונומיקה ואמוניה",
    )

    @model_validator(mode="after")
    def both_languages(self) -> "QualityRules":
        if sorted(rule.language for rule in self.scripts) != ["en", "he"]:
            raise ValueError("exactly one script rule per supported language is required")
        return self


DEFAULT_RULES = QualityRules()
