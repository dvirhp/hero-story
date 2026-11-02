"""Application factory; resources initialize during lifespan, with no LLM calls."""

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from storyforge.api.dependencies import Resources
from storyforge.api.errors import SafeRoute, http_error_handler, validation_error_handler
from storyforge.api.routes import router as story_router
from storyforge.api.routes_v2 import router as story_router_v2
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
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    health_router = APIRouter(route_class=SafeRoute)

    @health_router.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health() -> HealthResponse:
        return HealthResponse()

    app.include_router(health_router)
    app.include_router(story_router)
    app.include_router(story_router_v2)
    return app
