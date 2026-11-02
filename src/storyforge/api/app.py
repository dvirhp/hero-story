"""Application factory; resources initialize during lifespan, with no LLM calls."""

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI

from storyforge.api.dependencies import Resources
from storyforge.development.defaults import load_default_profiles
from storyforge.domain.base import Contract


class HealthResponse(Contract):
    status: Literal["ok"] = "ok"


def create_app(*, resources: Resources | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.resources = resources if resources is not None else Resources(profiles=load_default_profiles())
        try:
            yield
        finally:
            app.state.resources = None

    app = FastAPI(title="StoryForge AI", version="0.1.0", debug=False, lifespan=lifespan)

    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health() -> HealthResponse:
        return HealthResponse()

    return app
