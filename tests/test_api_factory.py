import httpx

from storyforge.api.app import create_app
from storyforge.llm.fake import FakeProvider


def test_factory_and_health_make_no_provider_calls(run_async, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Provider called during health/startup")
    monkeypatch.setattr(FakeProvider, "generate", forbidden)
    first, second = create_app(), create_app()
    assert first is not second
    assert getattr(first.state, "resources", None) is None
    async def check():
        async with first.router.lifespan_context(first):
            assert first.state.resources.profiles.bands[0].min_months == 0
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=first), base_url="http://test") as client:
                response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
        assert first.state.resources is None
        assert getattr(second.state, "resources", None) is None
    run_async(check())
