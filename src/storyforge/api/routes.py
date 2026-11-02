"""HTTP transport only: validation, dependency wiring and status mapping."""

import json
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response
from pydantic import BeforeValidator

from storyforge.api.dependencies import get_engine
from storyforge.api.errors import SafeRoute, public_failure, request_id
from storyforge.api.execution import execute_request
from storyforge.domain.generation import (
    GenerationFailure, GenerationResult, GenerationSuccess, generation_result_adapter,
)
from storyforge.domain.story import StoryRequest
from storyforge.orchestration.engine import StoryEngine


def _http_json_contract(value: object) -> StoryRequest:
    # FastAPI parses JSON before Pydantic. Re-enter JSON validation mode so JSON
    # arrays work for immutable tuple fields without coercing ages or weakening
    # the existing strict domain contracts. Unsupported values still fail.
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return StoryRequest.model_validate_json(json.dumps(value, ensure_ascii=True, allow_nan=False))


HTTPStoryRequest = Annotated[StoryRequest, BeforeValidator(_http_json_contract)]
router = APIRouter(route_class=SafeRoute)
_ERRORS = {status: {"model": GenerationFailure, "description": description}
           for status, description in {
               400: "Input content-policy rejection", 422: "Invalid input or generated quality rejection",
               499: "Generation cancelled (best effort after disconnect)", 500: "Internal failure",
               502: "Provider output/refusal or unsafe output", 503: "Provider unavailable or resource budget exhausted",
               504: "Generation deadline exceeded",
           }.items()}


@router.post("/v1/stories/generate", response_model=GenerationSuccess, responses=_ERRORS,
             tags=["Stories"], summary="Generate using the bounded engine (local fake provider by default)")
async def generate_story(
    payload: Annotated[HTTPStoryRequest, Body()], request: Request,
    engine: Annotated[StoryEngine, Depends(get_engine)],
) -> GenerationSuccess | Response:
    result = await execute_request(request, payload, engine, request_id(request))
    # Validate even dependency overrides; response failures are caught by SafeRoute.
    result = generation_result_adapter.validate_python(result)
    if isinstance(result, GenerationFailure):
        return public_failure(request, result)
    if result.request_id != request_id(request):
        raise ValueError("Engine result correlation does not match the request")
    return result
