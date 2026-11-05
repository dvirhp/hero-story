"""Observed-behavior probes, not semantic quality approval or engine fixes.

All text is synthetic. Several tests deliberately demonstrate an accepted quality
gap. A pass means the observation is reproduced, not that the manuscript is good.
"""
import json
from pathlib import Path

import pytest

from storyforge.config import AppSettings
from storyforge.development.v2 import load_profiles_v2
from storyforge.domain.generation import GenerationError
from storyforge.domain.story_v2 import StoryRequestV2
from storyforge.llm.fake import FakeProvider, FakeStep
from storyforge.llm.fixtures import LocalFixtureProvider
from storyforge.llm.fixtures_v2 import fixture_steps_v2
from storyforge.orchestration.budget import BudgetLimits
from storyforge.orchestration.engine import StoryEngine
from storyforge.quality.gate import assess_story
from storyforge.validation.normalization_v2 import normalize_v2

SETTINGS = AppSettings(planner_output_tokens=5000, writer_output_tokens=20000, max_input_tokens=64000)
LIMITS = BudgetLimits(max_total_tokens=260000)
ROY = Path(__file__).resolve().parents[1] / 'docs/examples/roy-alphabet-request.v2.he.json'


def context(language='en', age=36, pages=3, **changes):
    return normalize_v2(StoryRequestV2(language=language, age_months=age, page_count=pages,
                                     display_name='אור' if language == 'he' else 'Or',
                                     theme='לילה' if language == 'he' else 'Night', **changes),
                        load_profiles_v2(), settings=SETTINGS)


def execute(run_async, profiles, brief, provider):
    engine = StoryEngine(provider, profiles, settings=SETTINGS, limits=LIMITS, contract_version='2')
    return run_async(engine.generate(brief.request))


@pytest.mark.parametrize('language', ['he', 'en'])
@pytest.mark.parametrize('age', [0, 36, 120])
def test_identical_whole_pages_are_accepted_by_documented_policy(run_async, profiles, language, age):
    brief = context(language, age, pages=6)
    result = execute(run_async, profiles, brief, FakeProvider(fixture_steps_v2(brief)))
    assert result.status == 'success'
    assert len({p.text for p in result.story.pages}) == 1
    assert any(i.code == 'FORMULAIC_PAGE_REPETITION' and i.severity == 'advisory' for i in result.quality.issues)


@pytest.mark.parametrize('language', ['he', 'en'])
def test_contradictory_character_facts_can_pass(run_async, profiles, language):
    brief = context(language)
    plan, writer = fixture_steps_v2(brief)
    raw = json.loads(writer.response_json)
    # Contradictory facts are intentionally synthetic, with no private manuscript.
    phrases = (['אור מצא כדור אדום.', 'אור לא מצא שום כדור.', 'אור מצא כדור כחול.']
               if language == 'he' else
               ['Or found a red ball.', 'Or never found any ball.', 'Or found a blue ball.'])
    filler = 'אורח' if language == 'he' else 'gentle'
    for page, phrase in zip(raw['pages'], phrases, strict=True):
        words = phrase.split()
        words += [filler] * (brief.constraints.words_per_page.minimum - len(words))
        page['sentence_units'] = [' '.join(words)]
    result = execute(run_async, profiles, brief, FakeProvider((plan, FakeStep(response_json=json.dumps(raw)))))
    assert result.status == 'success' and result.quality.passed
    assert len(result.usage.attempts) == 2
    assert any(i.code == 'NARRATIVE_COVERAGE_REVIEW' for i in result.quality.issues)


def test_wrong_final_form_mapping_is_not_linguistically_validated(run_async, profiles):
    raw = json.loads(ROY.read_text(encoding='utf-8'))
    # Deliberately replace the canonical fixture's base of final kaf with aleph.
    final_target = next(t for t in raw['structure']['targets'] if t['label'] == 'ך')
    assert final_target['base_form'] == 'כ'
    final_target['base_form'] = 'א'
    brief = normalize_v2(StoryRequestV2.model_validate_json(json.dumps(raw)), load_profiles_v2(), settings=SETTINGS)
    result = execute(run_async, profiles, brief, FakeProvider(fixture_steps_v2(brief)))
    assert result.status == 'success' and result.quality.passed
    assert result.story.page_count == 27


def test_latin_script_is_not_english_fluency_validation(run_async, profiles):
    brief = context()
    plan, writer = fixture_steps_v2(brief)
    raw = json.loads(writer.response_json)
    for page in raw['pages']:
        page['sentence_units'] = ['Or ' + ' '.join(['zqxv'] * (brief.constraints.words_per_page.minimum - 1))]
    result = execute(run_async, profiles, brief, FakeProvider((plan, FakeStep(response_json=json.dumps(raw)))))
    assert result.status == 'success'
    assert not any(i.code == 'SCRIPT_MISMATCH' for i in result.quality.issues)


def test_sentence_entry_count_is_not_sentence_grammar():
    brief = context(pages=1, story_type='educational', structure={
        'targets': ({'target_id': 'moon', 'label': 'moon'},),
        'sentence_units_per_page': {'minimum': 1, 'maximum': 1}})
    raw = json.loads(fixture_steps_v2(brief)[1].response_json)
    phrase = 'Or sees the moon. The moon is bright. Or waves.'
    words = phrase.split()
    words += ['gentle'] * (brief.constraints.words_per_page.minimum - len(words))
    raw['pages'][0]['sentence_units'] = [' '.join(words)]
    report = assess_story(raw, brief)
    assert report.passed
    assert not any(i.code == 'SENTENCE_UNIT_COUNT' for i in report.issues)


def test_local_fake_fixture_overshoots_density_at_multiword_unit_boundary(run_async, profiles):
    # D-01: admitted request; one-word entries are a feasible domain witness.
    raw = dict(language='en', age_months=0, page_count=1, display_name='Or Lee', theme='Night',
               story_type='educational', structure={'targets': [{'target_id': 'moon', 'label': 'moon'}],
               'sentence_units_per_page': {'minimum': 15, 'maximum': 15}})
    request = StoryRequestV2.model_validate_json(json.dumps(raw))
    brief = normalize_v2(request, load_profiles_v2(), settings=SETTINGS)
    candidate = json.loads(fixture_steps_v2(brief)[1].response_json)
    assert len(candidate['pages'][0]['sentence_units']) == 15
    assert sum(len(unit.split()) for unit in candidate['pages'][0]['sentence_units']) == 16
    assert candidate['pages'][0]['sentence_units'].count('.') == 1
    assert not assess_story(candidate, brief).passed
    # A valid typed witness fits exactly 15 words/entries and preserves the name
    # in the derived text (units are joined by a space; punctuation is optional).
    witness = json.loads(json.dumps(candidate))
    witness['pages'][0]['sentence_units'] = ['Or', 'Lee', 'moon'] + ['soft'] * 12
    assert assess_story(witness, brief).passed
    result = execute(run_async, profiles, brief, LocalFixtureProvider())
    assert result.status == 'failure' and result.error.code == 'BUDGET_EXCEEDED'
    assert len(result.usage.attempts) == 3
    assert [a.error.code if a.error else None for a in result.usage.attempts] == [
        None, 'PROVIDER_OUTPUT_INVALID', 'PROVIDER_OUTPUT_INVALID']


@pytest.mark.parametrize('kind,expected,calls', [
    ('malformed', 'BUDGET_EXCEEDED', 3), ('density', 'BUDGET_EXCEEDED', 3),
    ('personalization', 'QUALITY_REJECTED', 3), ('refusal', 'PROVIDER_REFUSED', 2),
    ('unavailable', 'PROVIDER_UNAVAILABLE', 2),
])
def test_failure_classification_retains_attempt_evidence(run_async, profiles, kind, expected, calls):
    brief = context(pages=1)
    plan, writer = fixture_steps_v2(brief)
    if kind == 'malformed':
        bad = FakeStep(response_json='{}')
    elif kind in ('density', 'personalization'):
        raw = json.loads(writer.response_json)
        raw['pages'][0]['sentence_units'] = (['Or'] if kind == 'density' else
            [unit.replace('Or', 'Someone') for unit in raw['pages'][0]['sentence_units']])
        bad = FakeStep(response_json=json.dumps(raw))
    else:
        code = 'PROVIDER_REFUSED' if kind == 'refusal' else 'PROVIDER_UNAVAILABLE'
        bad = FakeStep(error=GenerationError(code=code, stage='writer', retryable=False, message='private-canary'))
    provider = FakeProvider((plan, bad, bad))
    result = execute(run_async, profiles, brief, provider)
    assert result.status == 'failure' and result.error.code == expected
    assert len(provider.calls) == len(result.usage.attempts) == calls
    assert not hasattr(result, 'story')
    assert 'private-canary' not in result.model_dump_json()
    if kind in ('malformed', 'density'):
        assert all(a.error.code == 'PROVIDER_OUTPUT_INVALID' for a in result.usage.attempts[1:])
    if kind == 'personalization':
        assert any(i.code == 'PERSONALIZATION_MISSING' for i in result.quality.issues)
        assert result.usage.attempts[-1].outcome == 'success'  # Valid transport/output, rejected by gate.
