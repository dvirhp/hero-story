"""Resolve immutable profile context and reject unsafe text before generation."""

from pydantic import ValidationError

from storyforge.development.models import DevelopmentConfig
from storyforge.development.resolver import resolve_profile
from storyforge.domain.generation import GenerationError
from storyforge.domain.story import NormalizedBrief, StoryRequest
from storyforge.quality.rules import DEFAULT_RULES, QualityRules
from storyforge.quality.text import contains_prohibited_directive, forbidden_controls, string_values


class NormalizationError(ValueError):
    """A safe structured error; never contains rejected input or validation details."""

    def __init__(self, error: GenerationError) -> None:
        self.error = error
        super().__init__(error.message)


def normalize_request(
    request: StoryRequest, config: DevelopmentConfig, rules: QualityRules = DEFAULT_RULES,
) -> NormalizedBrief:
    """Preserve supplied text exactly; normalization only resolves typed context."""
    if not isinstance(request, StoryRequest):
        raise NormalizationError(GenerationError(
            code="INPUT_INVALID", stage="validation", retryable=False,
            message="Supply a validated StoryRequest"))
    try:
        # Also defend against invalid model_construct/model_copy instances.
        checked = StoryRequest.model_validate(request.model_dump(warnings=False))
    except ValidationError:
        raise NormalizationError(GenerationError(
            code="INPUT_INVALID", stage="validation", retryable=False,
            message="Request does not match the supported input contract")) from None
    values = tuple(string_values(checked.model_dump()))
    if any(forbidden_controls(value) for value in values):
        raise NormalizationError(GenerationError(
            code="INPUT_INVALID", stage="validation", retryable=False,
            message="Remove prohibited Unicode controls from the request"))
    if any(contains_prohibited_directive(value, rules.prohibited_directives) for value in values):
        raise NormalizationError(GenerationError(
            code="POLICY_REJECTED", stage="validation", retryable=False,
            message="Request contains a prohibited dangerous directive"))
    profile = resolve_profile(config, checked.age_months, checked.language)
    return NormalizedBrief(request=checked, profile=profile, language_rubric_version=rules.rubric_version)
