"""Synthetic v2 contract fixtures; not a story-quality demonstration."""

import re

from storyforge.domain.generation import GenerationError
from storyforge.domain.story import PlotElements
from storyforge.domain.story_v2 import NormalizedBriefV2, PageIntentV2, StoryPageV2, StoryPlanV2, StoryV2
from storyforge.llm.fake import FakeStep


def _cuts(text: str) -> tuple[int, ...]:
    """Spaces that can be replaced by the derived-text join without rewriting.

    Preserve multi-space names and labels, including their remaining whitespace.
    A tab-only gap is indivisible because joining units would introduce a space.
    """
    return tuple(match.start() + match.group().index(" ") for match in re.finditer(r"\s+", text)
                 if match.start() > 0 and match.end() < len(text) and " " in match.group())


def _units(text: str, count: int) -> tuple[str, ...]:
    cuts = _cuts(text)
    selected = tuple(cuts[i * len(cuts) // count] for i in range(1, count))
    starts = (0,) + tuple(cut + 1 for cut in selected)
    ends = selected + (len(text),)
    units = tuple(text[start:end] for start, end in zip(starts, ends, strict=True))
    # Entry count is not sentence grammar. Punctuation at every split would
    # interrupt multiword names/labels and could create punctuation-only words.
    return units[:-1] + (units[-1] + ".",)


def fixture_steps_v2(brief: NormalizedBriefV2) -> tuple[FakeStep, FakeStep]:
    request, profile = brief.request, brief.profile
    targets = request.structure.targets if request.structure else (None,) * request.page_count
    he = request.language == "he"
    title = request.requested_title or ("לילה" if he else "Night")
    plan = StoryPlanV2(
        page_count=request.page_count, language=request.language, title_concept=title,
        protagonist=request.display_name, strategy=profile.requirements.strategy,
        pages=tuple(PageIntentV2(page_number=i, target_id=target.target_id if target else None,
                                intent="גילוי עדין" if he else "A gentle discovery",
                                progression=f"רגע {i}" if he else f"Moment {i}")
                    for i, target in enumerate(targets, 1)),
        plot=PlotElements(goal="מטרה" if he else "A goal", obstacle_or_choices="בחירה" if he else "A choice",
                          resolution="שלווה" if he else "Reassurance")
        if profile.requirements.strategy in ("simple_goal", "connected_scenes") else None,
    )
    pages = []
    for index, target in enumerate(targets, 1):
        words = [request.display_name + ","]
        if target:
            words.extend((target.label, target.base_form or "", target.example_word or ""))
        words = [word for word in words if word]
        filler = ("אור", "רך", "לילה", "נעים") if he else ("soft", "light", "gentle", "night")
        count = max(brief.constraints.words_per_page.minimum,
                    (brief.constraints.sentence_units_per_page.minimum if brief.constraints.sentence_units_per_page else 1))
        while len(" ".join(words).split()) < count:
            words.append(filler[len(words) % len(filler)])
        units_count = brief.constraints.sentence_units_per_page.minimum if brief.constraints.sentence_units_per_page else 1
        while len(_cuts(" ".join(words))) + 1 < units_count and len(" ".join(words).split()) < brief.constraints.words_per_page.maximum:
            words.append(filler[len(words) % len(filler)])
        text = " ".join(words)
        if (len(_cuts(text)) + 1 < units_count
                or len(text.split()) > brief.constraints.words_per_page.maximum):
            # Some admitted combinations cannot be built by this minimal fixture
            # strategy. Fail explicitly rather than fabricate empty/padded units.
            return FakeStep(response_json=plan.model_dump_json()), FakeStep(error=GenerationError(
                code="PROVIDER_OUTPUT_INVALID", stage="writer", retryable=False,
                message="Synthetic fixture cannot satisfy the supplied text constraints"))
        units = _units(text, units_count)
        pages.append(StoryPageV2(page_id=f"p{index}", page_number=index,
                                 target_id=target.target_id if target else None, sentence_units=units))
    story = StoryV2(page_count=request.page_count, title=title, language=request.language,
                    direction="rtl" if he else "ltr", profile_id=profile.band_id, profile_version=profile.version,
                    pages=tuple(pages))
    return FakeStep(response_json=plan.model_dump_json()), FakeStep(response_json=story.model_dump_json())
