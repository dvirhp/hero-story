"""Resolve requested book structure separately from developmental age guidance."""

from storyforge.config import AppSettings
from storyforge.development.models import WordRange
from storyforge.development.v2 import DevelopmentProfilesV2, resolve_v2
from storyforge.domain.generation import GenerationError
from storyforge.domain.story_v2 import BookConstraints, NormalizedBriefV2, StoryRequestV2
from storyforge.quality.rules import DEFAULT_RULES, QualityRules
from storyforge.quality.text import contains_prohibited_directive, forbidden_controls, string_values
from storyforge.validation.normalization import NormalizationError
from storyforge.validation.page_policy import PagePolicy


def normalize_v2(request: StoryRequestV2, profiles: DevelopmentProfilesV2, *,
                 settings: AppSettings = AppSettings(), page_policy: PagePolicy = PagePolicy(),
                 rules: QualityRules = DEFAULT_RULES) -> NormalizedBriefV2:
    try:
        if not isinstance(request, StoryRequestV2):
            raise ValueError()
        checked = StoryRequestV2.model_validate(request.model_dump(warnings=False))
        values = tuple(string_values(checked.model_dump()))
        if any(forbidden_controls(value) for value in values):
            raise ValueError()
        if any(contains_prohibited_directive(value, rules.prohibited_directives) for value in values):
            raise NormalizationError(GenerationError(code="POLICY_REJECTED", stage="validation", retryable=False,
                                                     message="Request contains a prohibited dangerous directive"))
        if not page_policy.minimum_pages <= checked.page_count <= page_policy.maximum_pages:
            raise ValueError()
        profile = resolve_v2(profiles, checked.age_months, checked.language)
        words = next(item.words_per_page for item in profile.requirements.densities
                     if item.density == checked.text_density)
        structure = checked.structure
        if (structure and structure.sentence_units_per_page
                and structure.sentence_units_per_page.minimum > words.maximum):
            raise ValueError("At least one word per sentence unit must fit the page density")
        allocation = page_policy.allocate(checked.page_count, words.maximum, checked.language, settings)
        constraints = BookConstraints(
            page_count=checked.page_count, words_per_page=words,
            total_words=WordRange(minimum=checked.page_count * words.minimum, maximum=checked.page_count * words.maximum),
            target_ids=tuple(target.target_id for target in structure.targets) if structure else (),
            sentence_units_per_page=structure.sentence_units_per_page if structure else None,
            policy_version=page_policy.version,
        )
        return NormalizedBriefV2(request=checked, profile=profile, constraints=constraints, execution=allocation,
                                 language_rubric_version=rules.rubric_version)
    except NormalizationError:
        raise
    except OverflowError:
        raise NormalizationError(GenerationError(code="BUDGET_EXCEEDED", stage="validation", retryable=False,
                                                 message="Requested book exceeds configured execution capacity")) from None
    except (ValueError, TypeError, AttributeError, StopIteration):
        raise NormalizationError(GenerationError(code="INPUT_INVALID", stage="validation", retryable=False,
                                                 message="Request does not match the supported input contract")) from None
