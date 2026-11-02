"""Local scripted generation smoke demo. Prints metadata only, never child text."""

import argparse
import asyncio
import json

from storyforge.development.defaults import load_default_profiles
from storyforge.domain.story import PageIntent, PlotElements, Story, StoryPage, StoryPlan, StoryRequest
from storyforge.llm.fake import FakeProvider, FakeStep
from storyforge.orchestration.engine import StoryEngine
from storyforge.validation.normalization import normalize_request


async def run_demo(language: str = "en", age_months: int = 0) -> dict[str, object]:
    """All names/text are synthetic fixtures, not LLM-written sample literature."""
    profiles = load_default_profiles()
    request = StoryRequest(language=language, age_months=age_months,
                           display_name="נורי" if language == "he" else "Nori",
                           theme="אור ירח" if language == "he" else "Moonlight")
    brief = normalize_request(request, profiles)
    profile = brief.profile
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
    provider = FakeProvider((FakeStep(response_json=plan.model_dump_json()), FakeStep(response_json=story.model_dump_json())))
    result = await StoryEngine(provider, profiles).generate(request)
    return {
        "status": result.status, "request_id": result.request_id, "language": language,
        "profile": profile.band_id, "attempts": len(result.usage.attempts),
        "unknown_usage": result.usage.has_unknown_usage,
        "upper_estimated_cost_usd": result.usage.upper_estimated_cost_usd,
        "error_code": result.error.code if result.status == "failure" else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an offline StoryForge fixture through LangGraph")
    parser.add_argument("--language", choices=("en", "he"), default="en")
    parser.add_argument("--age-months", type=int, default=0)
    args = parser.parse_args()
    if args.age_months < 0:
        parser.error("age-months must be nonnegative")
    result = asyncio.run(run_demo(args.language, args.age_months))
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
