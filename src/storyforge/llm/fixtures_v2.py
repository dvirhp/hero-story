"""Synthetic v2 contract fixtures; not a story-quality demonstration."""

import json

from storyforge.domain.story import PlotElements
from storyforge.domain.story_v2 import NormalizedBriefV2, PageIntentV2, StoryPageV2, StoryPlanV2, StoryV2
from storyforge.llm.fake import FakeStep


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
        tokens = words  # Keep multiword names and learning labels intact within a unit.
        units = tuple(" ".join(tokens[i * len(tokens) // units_count:(i + 1) * len(tokens) // units_count]) + "."
                      for i in range(units_count))
        pages.append(StoryPageV2(page_id=f"p{index}", page_number=index,
                                 target_id=target.target_id if target else None, sentence_units=units))
    story = StoryV2(page_count=request.page_count, title=title, language=request.language,
                    direction="rtl" if he else "ltr", profile_id=profile.band_id, profile_version=profile.version,
                    pages=tuple(pages))
    return FakeStep(response_json=plan.model_dump_json()), FakeStep(response_json=story.model_dump_json())
