"""HTTP mappings and fixed public failures; never echo framework diagnostics."""

from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException
from starlette.responses import Response

from storyforge.domain.generation import GenerationError, GenerationFailure, UsageSummary

_STATUS = {
    "INPUT_INVALID": 422, "PROVIDER_OUTPUT_INVALID": 502, "PROVIDER_UNAVAILABLE": 503,
    "PROVIDER_REFUSED": 502, "CONFIGURATION_ERROR": 500, "DEADLINE_EXCEEDED": 504,
    "CANCELLED": 499, "BUDGET_EXCEEDED": 503, "QUALITY_REJECTED": 422,
}
_MESSAGES = {
    "INPUT_INVALID": "Request does not match the supported input contract",
    "POLICY_REJECTED": "Prohibited content or controls were detected",
    "PROVIDER_OUTPUT_INVALID": "Provider output did not match the required contract",
    "PROVIDER_UNAVAILABLE": "Provider temporarily unavailable",
    "PROVIDER_REFUSED": "Provider declined the generation request",
    "CONFIGURATION_ERROR": "Internal request failure",
    "DEADLINE_EXCEEDED": "Generation deadline exceeded",
    "CANCELLED": "Generation cancelled",
    "BUDGET_EXCEEDED": "Generation cannot continue under configured resource limits",
    "QUALITY_REJECTED": "Generated draft failed quality checks; the request may be valid",
}


def request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    if value is None:
        value = str(uuid4())
        request.state.request_id = value
    return value


def response_headers(request: Request) -> dict[str, str]:
    return {"X-Request-ID": request_id(request), "Cache-Control": "no-store"}


def failure_status(error: GenerationError) -> int:
    if error.code == "POLICY_REJECTED":
        return 400 if error.stage == "validation" else 502
    return _STATUS[error.code]


def public_failure(request: Request, failure: GenerationFailure) -> JSONResponse:
    # Reuse the result schema, but never relay arbitrary dependency diagnostics.
    safe_error = GenerationError(
        code=failure.error.code, stage=failure.error.stage, retryable=failure.error.retryable,
        message=_MESSAGES[failure.error.code],
    )
    safe = GenerationFailure(request_id=request_id(request), usage=failure.usage,
                             total_latency_seconds=failure.total_latency_seconds,
                             quality=failure.quality, error=safe_error)
    return JSONResponse(safe.model_dump(mode="json"), status_code=failure_status(safe_error),
                        headers=response_headers(request))


def boundary_failure(request: Request, *, internal: bool = False) -> JSONResponse:
    failure = GenerationFailure(
        request_id=request_id(request), usage=UsageSummary(), total_latency_seconds=0.0,
        error=GenerationError(code="CONFIGURATION_ERROR" if internal else "INPUT_INVALID",
                              stage="validation", retryable=False,
                              message="Internal request failure" if internal else "Invalid request"),
    )
    return public_failure(request, failure)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Do not stringify the exception, access .body or expose .errors(): they hold input.
    return boundary_failure(request)


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    response = boundary_failure(request, internal=exc.status_code >= 500)
    response.status_code = exc.status_code
    # Preserve the protocol-required Allow header, never arbitrary exception headers/detail.
    if exc.status_code == 405 and exc.headers and "Allow" in exc.headers:
        response.headers["Allow"] = exc.headers["Allow"]
    return response


class SafeRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        handler = super().get_route_handler()

        async def safe_handler(request: Request) -> Response:
            request_id(request)
            try:
                response = await handler(request)
            except (RequestValidationError, HTTPException):
                raise  # Sanitized application handlers handle these.
            except Exception:
                # Catch within the route so server error middleware does not re-raise
                # private dependency/response-validation exceptions into server logs.
                response = boundary_failure(request, internal=True)
            response.headers.update(response_headers(request))
            return response

        return safe_handler
