"""Independent HTTP regressions: real ASGI/graph/gate, scripted offline provider."""
import asyncio
import json
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from storyforge.api.app import create_app
from storyforge.api.dependencies import Resources
from storyforge.config import AppSettings
from storyforge.development.v2 import load_profiles_v2
from storyforge.domain.generation import GenerationError
from storyforge.domain.story_v2 import StoryRequestV2
from storyforge.llm.fake import FakeProvider, FakeStep
from storyforge.llm.fixtures_v2 import fixture_steps_v2
from storyforge.orchestration.budget import BudgetLimits
from storyforge.validation.normalization_v2 import normalize_v2

SETTINGS = AppSettings(planner_output_tokens=5000, writer_output_tokens=20000, max_input_tokens=64000)
LIMITS = BudgetLimits(max_total_tokens=260000)
CASES = json.loads((Path(__file__).parent / 'fixtures/qa_v2_requests.json').read_text(encoding='utf-8'))


@pytest.fixture
def post(run_async, profiles):
    def call(payload, steps):
        provider = FakeProvider(tuple(steps))
        app = create_app(resources=Resources(profiles=profiles, settings=SETTINGS, limits=LIMITS, provider=provider))
        async def perform():
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                    return await client.post('/v2/stories/generate', json=payload,
                                             headers={'X-Request-ID': 'untrusted-client-id'})
        return run_async(perform()), provider
    return call


def steps_for(payload):
    request = StoryRequestV2.model_validate_json(json.dumps(payload, ensure_ascii=False))
    return fixture_steps_v2(normalize_v2(request, load_profiles_v2(), settings=SETTINGS))


def assert_envelope(response):
    data = response.json()
    UUID(data['request_id'])
    assert data['request_id'] == response.headers['X-Request-ID']
    assert response.headers['Cache-Control'] == 'no-store'
    assert data['request_id'] != 'untrusted-client-id'
    return data


@pytest.mark.parametrize('payload', CASES, ids=lambda p: f"{p['language']}-{p['age_months']}-{p['story_type']}")
def test_regression_requests(post, payload, caplog, capsys):
    response, provider = post(payload, steps_for(payload))
    assert response.status_code == 200, response.text
    data = assert_envelope(response)
    story = data['story']
    assert story['page_count'] == len(story['pages']) == payload['page_count']
    assert [p['page_number'] for p in story['pages']] == list(range(1, payload['page_count'] + 1))
    assert story['direction'] == ('rtl' if payload['language'] == 'he' else 'ltr')
    text = ' '.join(' '.join(p['sentence_units']) for p in story['pages'])
    assert payload['display_name'] in text  # Exact logical Unicode order, including combining marks.
    if 'structure' in payload:
        assert [p['target_id'] for p in story['pages']] == [t['target_id'] for t in payload['structure']['targets']]
    assert len(provider.calls) == len(data['usage']['attempts']) == 2
    assert not {'plan', 'draft', 'instructions', 'input_json', 'api_key'} & data.keys()
    captured = capsys.readouterr()
    assert payload['display_name'] not in caplog.text + captured.out + captured.err


@pytest.mark.parametrize('age', [0, 2, 3, 11, 12, 35, 36, 71, 72, 10000])
def test_http_age_never_selects_length(post, age):
    payload = {**CASES[0], 'age_months': age, 'page_count': 7}
    response, _ = post(payload, steps_for(payload))
    assert response.status_code == 200, response.text
    assert len(response.json()['story']['pages']) == 7


@pytest.mark.parametrize('change', [
    {'page_count': v} for v in [None, True, 0, -1, 1.5, '4', 'auto', 33]
] + [{'age_months': True}, {'language': 'ja'}, {'display_name': 'private\u202ename'},
     {'api_key': 'dummy-private-credential'}, {'birth_date': 'private-date'}])
def test_invalid_input_is_private_and_makes_zero_calls(post, change):
    response, provider = post({**CASES[0], **change}, ())
    data = assert_envelope(response)
    assert response.status_code == 422
    assert data['error']['code'] == 'INPUT_INVALID'
    assert provider.calls == () and data['usage']['attempts'] == []
    assert 'private' not in response.text and 'story' not in data


def test_missing_page_count_never_falls_back_to_age(post):
    payload = {k: v for k, v in CASES[0].items() if k != 'page_count'}
    response, provider = post(payload, ())
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'INPUT_INVALID'
    assert not provider.calls


@pytest.mark.parametrize('mutation', ['short', 'target_order'])
def test_http_never_accepts_incomplete_or_reordered_education(post, mutation):
    payload = CASES[3]
    plan, story = steps_for(payload)
    raw = json.loads(story.response_json)
    if mutation == 'short':
        raw['pages'].pop()
        raw['page_count'] -= 1
    else:
        raw['pages'][0]['target_id'], raw['pages'][1]['target_id'] = (
            raw['pages'][1]['target_id'], raw['pages'][0]['target_id'])
    bad = FakeStep(response_json=json.dumps(raw))
    response, provider = post(payload, (plan, bad, bad))
    assert response.status_code != 200
    data = assert_envelope(response)
    assert data['status'] == 'failure' and 'story' not in data
    assert len(provider.calls) == 3


@pytest.mark.parametrize('kind', ['refused', 'unavailable', 'malformed', 'timeout', 'unsafe', 'quality'])
def test_http_failures_budget_and_no_failed_draft(post, kind, caplog, capsys):
    payload = CASES[0]
    plan, story = steps_for(payload)
    if kind in ('refused', 'unavailable'):
        code = 'PROVIDER_REFUSED' if kind == 'refused' else 'PROVIDER_UNAVAILABLE'
        steps = (FakeStep(error=GenerationError(code=code, stage='planner', retryable=False,
                                               message='dummy-private-credential')),)
        expected, status, calls = code, 502 if kind == 'refused' else 503, 1
    elif kind == 'unsafe':
        steps = (FakeStep(response_json='{"text":"Drink bleach now!"}'),)
        expected, status, calls = 'POLICY_REJECTED', 502, 1
    elif kind == 'quality':
        raw = json.loads(story.response_json)
        for page in raw['pages']:
            page['sentence_units'] = [u.replace(payload['display_name'], 'Someone') for u in page['sentence_units']]
        bad = FakeStep(response_json=json.dumps(raw))
        steps = (plan, bad, bad)
        expected, status, calls = 'QUALITY_REJECTED', 422, 3
    else:
        bad = FakeStep(response_json='{}', latency_seconds=1000.0 if kind == 'timeout' else 0.0)
        steps = (bad, bad, bad)
        expected, status, calls = 'BUDGET_EXCEEDED', 503, 2
    response, provider = post(payload, steps)
    data = assert_envelope(response)
    assert response.status_code == status, response.text
    assert data['error']['code'] == expected
    assert len(provider.calls) == len(data['usage']['attempts']) == calls
    assert not {'story', 'draft', 'plan'} & data.keys()
    captured = capsys.readouterr()
    public = response.text + caplog.text + captured.out + captured.err
    assert 'dummy-private-credential' not in public
    assert payload['display_name'] not in public


def test_concurrent_http_requests_keep_child_content_and_ledgers_isolated(run_async, profiles, caplog):
    # Real request-local LocalFixtureProvider composition, not a shared fake queue.
    app = create_app(resources=Resources(profiles=profiles, settings=SETTINGS, limits=LIMITS))
    payloads = [{**CASES[0], 'display_name': 'AlphaPrivate', 'page_count': 2},
                {**CASES[1], 'display_name': 'בטאפרטי', 'page_count': 3}]
    async def perform():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                return await asyncio.gather(*(client.post('/v2/stories/generate', json=p) for p in payloads))
    responses = run_async(perform())
    ids = set()
    for index, response in enumerate(responses):
        assert response.status_code == 200
        data = assert_envelope(response)
        ids.add(data['request_id'])
        assert len(data['story']['pages']) == payloads[index]['page_count']
        assert payloads[index]['display_name'] in response.text
        assert payloads[1-index]['display_name'] not in response.text
        assert len(data['usage']['attempts']) == 2
        assert [a['attempt_number'] for a in data['usage']['attempts']] == [1, 2]
        assert data['usage']['has_unknown_usage']
    assert len(ids) == 2
    assert all(p['display_name'] not in caplog.text for p in payloads)


def test_transient_provider_failure_recovers_with_one_shared_budget(post):
    payload = CASES[0]
    plan, story = steps_for(payload)
    transient = FakeStep(error=GenerationError(code='PROVIDER_UNAVAILABLE', stage='planner',
                                              retryable=True, message='private-provider-canary'))
    response, provider = post(payload, (transient, plan, story))
    assert response.status_code == 200
    data = assert_envelope(response)
    assert len(provider.calls) == len(data['usage']['attempts']) == 3
    assert [a['outcome'] for a in data['usage']['attempts']] == ['failure', 'success', 'success']
    assert len(data['story']['pages']) == payload['page_count']
    assert 'private-provider-canary' not in response.text
