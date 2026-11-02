"""Request-scoped execution and disconnect monitoring; no detached jobs."""

import asyncio

from fastapi import Request

from storyforge.domain.generation import GenerationError, GenerationFailure, GenerationResult, UsageSummary
from storyforge.domain.story import StoryRequest
from storyforge.orchestration.engine import StoryEngine


async def _disconnected(request: Request) -> None:
    # FastAPI has consumed the complete body before the endpoint starts. There
    # is no competing reader and no polling loop that might consume body data.
    while True:
        message = await request.receive()
        if message["type"] == "http.disconnect":
            return


async def execute_request(
    request: Request, payload: StoryRequest, engine: StoryEngine, request_id: str,
) -> GenerationResult:
    generation = asyncio.create_task(engine.generate(payload, request_id=request_id))
    disconnect = asyncio.create_task(_disconnected(request))
    try:
        done, _ = await asyncio.wait((generation, disconnect), return_when=asyncio.FIRST_COMPLETED)
        if disconnect in done:
            disconnect.result()  # Propagate an unexpected receive failure safely.
            generation.cancel()
            finished = await asyncio.gather(generation, return_exceptions=True)
            result = finished[0]
            # Preserve the engine's ledger when cooperative cancellation returned it.
            if isinstance(result, GenerationFailure):
                return GenerationFailure(
                    request_id=request_id, usage=result.usage, total_latency_seconds=result.total_latency_seconds,
                    quality=result.quality,
                    error=GenerationError(code="CANCELLED", stage=result.error.stage, retryable=False,
                                          message="Generation cancelled after disconnect"),
                )
            return GenerationFailure(
                request_id=request_id, usage=result.usage if hasattr(result, "usage") else UsageSummary(),
                total_latency_seconds=result.total_latency_seconds if hasattr(result, "total_latency_seconds") else 0.0,
                error=GenerationError(code="CANCELLED", stage="validation", retryable=False,
                                      message="Generation cancelled after disconnect"),
            )
        return await generation
    finally:
        # Also drains the generation task on ASGI cancellation. StoryEngine may
        # convert cancellation to a typed result, but no child task outlives us.
        for task in (generation, disconnect):
            if not task.done():
                task.cancel()
        await asyncio.gather(generation, disconnect, return_exceptions=True)
