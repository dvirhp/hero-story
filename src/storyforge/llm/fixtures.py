"""Synthetic local fixtures only; no model, semantic generation or network."""

import json

from storyforge.domain.story import NormalizedBrief, PageIntent, PlotElements, Story, StoryPage, StoryPlan
from storyforge.llm.fake import FakeProvider, FakeStep
from storyforge.llm.protocol import LLMRequest, OutputT, ProviderFailure, ProviderSuccess
from storyforge.quality.rules import DEFAULT_RULES, QualityRules


def fixture_steps(brief: NormalizedBrief) -> tuple[FakeStep, FakeStep]:
    """Build the two synthetic demo fixtures from an already normalized brief."""
    request, profile = brief.request, brief.profile
    language = request.language
    plan = StoryPlan(
        language=language, title_concept="לילה" if language == "he" else "Night",
        protagonist=request.display_name, strategy=profile.requirements.strategy,
        pages=tuple(PageIntent(page_number=i, intent="רגע שקט" if language == "he" else "A quiet moment")
                    for i in range(1, profile.requirements.hard.page_count + 1)),
        plot=(PlotElements(goal="מטרה" if language == "he" else "A goal",
                           obstacle_or_choices="בחירה" if language == "he" else "A choice",
                           resolution="שלווה" if language == "he" else "Reassurance")
              if profile.requirements.strategy in ("simple_goal", "connected_scenes") else None),
    )
    words = ("אור רך צליל שקט לילה נעים" if language == "he" else "soft light quiet sounds gentle night").split()
    count = profile.requirements.hard.words_per_page.minimum
    text = " ".join([request.display_name + ","] + [words[i % len(words)] for i in range(count - 1)]) + "."
    story = Story(
        title="לילה" if language == "he" else "Night", language=language,
        direction="rtl" if language == "he" else "ltr", profile_id=profile.band_id,
        profile_version=profile.version,
        pages=tuple(StoryPage(page_id=f"p{i}", page_number=i, text=text)
                    for i in range(1, profile.requirements.hard.page_count + 1)),
    )
    return FakeStep(response_json=plan.model_dump_json()), FakeStep(response_json=story.model_dump_json())


class LocalFixtureProvider:
    """Delegate each requested stage to one existing FakeProvider invocation.

    Useful for local HTTP demos with arbitrary valid briefs. No transport retries
    or stateful script queue; the orchestration engine still owns all limits.
    Text is repetitive fixture material and does not implement creative guidance.
    """

    def __init__(self, *, rules: QualityRules = DEFAULT_RULES) -> None:
        self._rules = rules

    async def generate(
        self, request: LLMRequest, output_schema: type[OutputT],
    ) -> ProviderSuccess[OutputT] | ProviderFailure:
        data = json.loads(request.input_json)
        brief = NormalizedBrief.model_validate_json(json.dumps(data["brief"], ensure_ascii=True))
        steps = fixture_steps(brief)
        step = steps[0 if request.stage == "planner" else 1]
        return await FakeProvider((step,), rules=self._rules).generate(request, output_schema)
