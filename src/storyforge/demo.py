"""Local scripted generation smoke demo. Prints metadata only, never child text."""

import argparse
import asyncio
import json

from storyforge.development.defaults import load_default_profiles
from storyforge.domain.story import StoryRequest
from storyforge.llm.fake import FakeProvider
from storyforge.llm.fixtures import fixture_steps
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
    provider = FakeProvider(fixture_steps(brief))
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
