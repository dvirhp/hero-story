"""Pure profile resolution; no I/O, provider, or graph dependencies."""

from pydantic import TypeAdapter

from storyforge.development.models import DevelopmentConfig, DevelopmentalProfile
from storyforge.domain.base import Language, NonNegativeInt

_AGE = TypeAdapter(NonNegativeInt)
_LANGUAGE = TypeAdapter(Language)


def resolve_profile(
    config: DevelopmentConfig, age_months: int, language: Language,
) -> DevelopmentalProfile:
    age = _AGE.validate_python(age_months, strict=True)
    language = _LANGUAGE.validate_python(language, strict=True)
    band = next(b for b in config.bands
                if b.min_months <= age and (b.max_months is None or age < b.max_months))
    requirements = next(p for p in band.languages if p.language == language)
    return DevelopmentalProfile(
        band_id=band.band_id, version=config.version, min_months=band.min_months,
        max_months=band.max_months, provisional=band.provisional, requirements=requirements,
    )
