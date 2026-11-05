"""Ownership is not implemented: no private Book endpoint may be reachable."""

import httpx
import pytest

from storyforge.api.app import create_app


@pytest.mark.parametrize("method,path",[("GET","/v3/books"),("GET","/v3/books/00000000-0000-4000-8000-000000000001"),
    ("POST","/v3/books/manual"),("POST","/v3/books/ai"),("POST","/v3/jobs/stories")])
def test_private_routes_remain_unmounted(run_async,method,path):
    async def run():
        app=create_app()
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
                response=await client.request(method,path,json={"title":"private-canary"})
                assert response.status_code==404
                assert "private-canary" not in response.text
                schema=(await client.get("/openapi.json")).json()
                assert "/v2/stories/generate" in schema["paths"]
                assert not any(route.startswith("/v3/") for route in schema["paths"])
    run_async(run())
