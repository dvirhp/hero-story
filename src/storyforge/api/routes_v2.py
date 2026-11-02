"""Explicit-length v2 HTTP boundary, sharing execution and safe failure handling."""

import json
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response
from pydantic import BeforeValidator

from storyforge.api.dependencies import get_engine_v2
from storyforge.api.errors import SafeRoute, public_failure, request_id
from storyforge.api.execution import execute_request
from storyforge.api.routes import _ERRORS
from storyforge.domain.generation import GenerationFailure
from storyforge.domain.generation_v2 import GenerationSuccessV2, generation_result_v2_adapter
from storyforge.domain.story_v2 import StoryRequestV2
from storyforge.orchestration.engine import StoryEngine


def _http_json_contract(value: object) -> StoryRequestV2:
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return StoryRequestV2.model_validate_json(json.dumps(value, ensure_ascii=True, allow_nan=False))


HTTPStoryRequestV2 = Annotated[StoryRequestV2, BeforeValidator(_http_json_contract)]
router = APIRouter(route_class=SafeRoute)


@router.post("/v2/stories/generate", response_model=GenerationSuccessV2, responses=_ERRORS,
             tags=["Stories"], summary="Generate exactly the requested number of pages")
async def generate_story_v2(
    payload: Annotated[HTTPStoryRequestV2, Body()], request: Request,
    engine: Annotated[StoryEngine, Depends(get_engine_v2)],
) -> GenerationSuccessV2 | Response:
    result = await execute_request(request, payload, engine, request_id(request))
    result = generation_result_v2_adapter.validate_python(result)
    if isinstance(result, GenerationFailure):
        return public_failure(request, result)
    expected_targets = tuple(target.target_id for target in payload.structure.targets) if payload.structure else ()
    if (result.request_id != request_id(request)
            or result.story.page_count != payload.page_count
            or result.resolved_constraints.target_ids != expected_targets
            or (payload.requested_title and result.story.title != payload.requested_title)):
        raise ValueError("Engine result does not match request")
    return result
