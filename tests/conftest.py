import asyncio

import pytest

from storyforge.development.defaults import load_default_profiles
from storyforge.development.resolver import resolve_profile
from storyforge.domain.story import NormalizedBrief, Story, StoryPage, StoryRequest

_loop = None


def pytest_sessionstart(session):
    # Windows asyncio creates a local socket pair during loop construction.
    # Construct it before pytest-socket's per-test guard; all test execution
    # (including provider coroutines) still runs with sockets disabled.
    global _loop
    _loop = asyncio.new_event_loop()


def pytest_sessionfinish(session, exitstatus):
    if _loop is not None:
        _loop.close()


@pytest.fixture
def run_async():
    return _loop.run_until_complete


@pytest.fixture
def profiles():
    return load_default_profiles()


@pytest.fixture
def make_brief(profiles):
    def factory(age=0, language="en", config=None):
        request = StoryRequest(language=language, display_name="אור" if language == "he" else "Or",
                               age_months=age, theme="לילה" if language == "he" else "Night")
        profile = resolve_profile(config or profiles, age, language)
        return NormalizedBrief(request=request, profile=profile, language_rubric_version="rubric-v1")
    return factory


@pytest.fixture
def make_story():
    def factory(brief, word_count=None):
        p = brief.profile
        hard = p.requirements.hard
        count = word_count if word_count is not None else hard.words_per_page.minimum
        word = "אור" if brief.request.language == "he" else "Or"
        return Story(title="לילה" if brief.request.language == "he" else "Night",
                     language=brief.request.language,
                     direction="rtl" if brief.request.language == "he" else "ltr",
                     profile_id=p.band_id, profile_version=p.version,
                     pages=tuple(StoryPage(page_id=f"p{i}", page_number=i,
                                           text=" ".join([word] * count))
                                 for i in range(1, hard.page_count + 1)))
    return factory
