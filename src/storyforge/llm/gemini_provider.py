"""One asynchronous Gemini Developer API call, with no SDK recovery loops."""

import asyncio
import math
import socket
import ssl
import time
from collections.abc import Callable
from email.utils import parsedate_to_datetime

import httpx
from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from storyforge.domain.generation import GenerationError, QualityReport, TokenUsage
from storyforge.domain.diagnostics import ProviderDiagnostic, diagnostic_for_code, diagnostic_for_http
from storyforge.llm.configuration import GeminiConfig, ModelCapabilities
from storyforge.llm.gemini_schema import gemini_schema
from storyforge.llm.protocol import LLMRequest, OutputT, ProviderFailure, ProviderSuccess
from storyforge.quality.gate import inspect_output_safety
from storyforge.quality.rules import DEFAULT_RULES, QualityRules


def create_gemini_client(config: GeminiConfig, *, http_client: httpx.AsyncClient | None = None) -> genai.Client:
    """Construct only; explicit key/backend/endpoint override SDK discovery.

    Close both client.aio and client. A supplied test transport is caller-owned.
    """
    return genai.Client(
        api_key=config.api_key.get_secret_value(), vertexai=False,
        http_options=types.HttpOptions(
            base_url="https://generativelanguage.googleapis.com", api_version="v1beta",
            timeout=max(1, math.ceil(config.timeout_seconds * 1000)),
            retry_options=types.HttpRetryOptions(attempts=1),
            client_args={"trust_env": False, "follow_redirects": False},
            async_client_args={"trust_env": False, "follow_redirects": False},
            httpx_async_client=http_client,
        ),
    )


async def close_gemini_client(client: genai.Client) -> None:
    try:
        await client.aio.aclose()
    finally:
        client.close()


def normalize_gemini_usage(raw: object) -> TokenUsage:
    """Gemini candidates exclude thoughts; domain output includes both."""
    try:
        prompt, candidates = raw.prompt_token_count, raw.candidates_token_count
        thoughts, total = raw.thoughts_token_count, raw.total_token_count
        if type(prompt) is not int or type(candidates) is not int or prompt < 0 or candidates < 0:
            raise ValueError("Incomplete usage")
        if thoughts is None:
            if type(total) is not int or total != prompt + candidates:
                raise ValueError("Unreported thinking usage")
            thoughts = 0
        if type(thoughts) is not int or thoughts < 0:
            raise ValueError("Invalid thinking usage")
        output = candidates + thoughts
        if total is not None and (type(total) is not int or total != prompt + output):
            raise ValueError("Unreconciled usage")
        if getattr(raw, "tool_use_prompt_token_count", None) not in (None, 0):
            raise ValueError("Unexpected tool usage")
        return TokenUsage(source="reported", input_tokens=prompt, output_tokens=output,
                          cached_input_tokens=raw.cached_content_token_count,
                          reasoning_output_tokens=thoughts)
    except (AttributeError, ValueError, TypeError, ValidationError):
        return TokenUsage(source="unknown")


def _retry_after(error: errors.APIError) -> float | None:
    response = error.response
    value = response.headers.get("retry-after") if response is not None else None
    if value is None:
        # Google RetryInfo can carry a server delay without an HTTP header.
        body = error.details.get("error") if isinstance(error.details, dict) else None
        details = body.get("details", []) if isinstance(body, dict) else []
        for detail in details if isinstance(details, list) else []:
            if isinstance(detail, dict) and detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo":
                delay = detail.get("retryDelay")
                if isinstance(delay, str) and delay.endswith("s"):
                    value = delay[:-1]
                    break
    if value is None:
        return None
    try:
        seconds = float(value)
    except (ValueError, TypeError):
        try:
            seconds = parsedate_to_datetime(value).timestamp() - time.time()
        except (ValueError, TypeError, OverflowError):
            return None
    return max(0.0, seconds) if math.isfinite(seconds) else None


def _transport_diagnostic(error: httpx.TransportError) -> ProviderDiagnostic:
    # Inspect only known exception types, never messages, URLs, headers or args.
    cause: BaseException | None = error
    for _ in range(5):
        if isinstance(cause, ssl.SSLError):
            return ProviderDiagnostic(category="tls_error")
        if isinstance(cause, socket.gaierror):
            return ProviderDiagnostic(category="dns_error")
        cause = cause.__cause__ if cause is not None else None
    return ProviderDiagnostic(category="connection_error" if isinstance(error, httpx.ConnectError) else "transport_error")


class GeminiProvider:
    provider_name = "gemini"

    def __init__(self, client: genai.Client, config: GeminiConfig,
                 capabilities: ModelCapabilities | tuple[ModelCapabilities, ...], *,
                 rules: QualityRules = DEFAULT_RULES, clock: Callable[[], float] = time.monotonic) -> None:
        self._client, self._config, self._rules, self._clock = client, config, rules, clock
        entries = (capabilities,) if isinstance(capabilities, ModelCapabilities) else capabilities
        self._capabilities = {entry.model: entry for entry in entries}
        if len(entries) != len(self._capabilities):
            raise ValueError("Duplicate model capabilities")

    async def generate(self, request: LLMRequest, output_schema: type[OutputT]) -> ProviderSuccess[OutputT] | ProviderFailure:
        started = self._clock()
        usage = TokenUsage(source="unknown")

        def failure(code: str, retryable: bool = False, *, quality=None, retry_after=None, diagnostic=None):
            messages = {
                "CONFIGURATION_ERROR": "Provider credentials, model or request configuration is invalid",
                "PROVIDER_UNAVAILABLE": "Provider temporarily unavailable",
                "DEADLINE_EXCEEDED": "Provider attempt timed out",
                "PROVIDER_OUTPUT_INVALID": "Provider output did not match the structured contract",
                "PROVIDER_REFUSED": "Provider declined to produce a story",
                "POLICY_REJECTED": "Provider output contains prohibited content or controls",
            }
            return ProviderFailure(provider="gemini", model=request.model, usage=usage,
                                   latency_seconds=max(0.0, self._clock() - started), quality=quality,
                                   retry_after_seconds=retry_after,
                                   provider_diagnostic=diagnostic or diagnostic_for_code(code),
                                   error=GenerationError(code=code, stage=request.stage, retryable=retryable,
                                                         message=messages[code]))

        cap = self._capabilities.get(request.model)
        if cap is None or request.max_output_tokens > cap.max_output_tokens:
            return failure("CONFIGURATION_ERROR")
        try:
            timeout = min(request.remaining_seconds, self._config.timeout_seconds)
            async with asyncio.timeout(timeout):
                response = await self._client.aio.models.generate_content(
                    model=request.model, contents=request.input_json,
                    config=types.GenerateContentConfig(
                        system_instruction=request.instructions, response_mime_type="application/json",
                        response_json_schema=gemini_schema(output_schema),
                        max_output_tokens=request.max_output_tokens,
                        thinking_config=(types.ThinkingConfig(thinking_level=cap.gemini_thinking_level,
                                                              include_thoughts=False)
                                         if cap.gemini_thinking_level is not None else None),
                        tools=[], automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                        automatic_continuation=False, store=False,
                        http_options=types.HttpOptions(timeout=max(1, math.ceil(timeout * 1000)),
                                                       retry_options=types.HttpRetryOptions(attempts=1)),
                    ),
                )
            usage = normalize_gemini_usage(response.usage_metadata)
            candidates = response.candidates or []
            texts, unexpected = [], False
            for candidate in candidates:
                for part in candidate.content.parts if candidate.content and candidate.content.parts else []:
                    if any(getattr(part, field, None) is not None for field in (
                        "function_call", "function_response", "executable_code", "code_execution_result",
                        "inline_data", "file_data", "tool_call", "tool_response",
                    )):
                        unexpected = True
                    if part.thought:
                        continue  # Never expose reasoning/signatures.
                    if isinstance(part.text, str):
                        texts.append(part.text)
                    # Reject tools/media even when a part also carries text.
                    if part.text is None:
                        unexpected = True
            text = "".join(texts)
            unsafe = inspect_output_safety(text, self._rules)
            if unsafe:
                return failure("POLICY_REJECTED", quality=QualityReport(
                    passed=False, issues=unsafe, check_version=self._rules.version,
                    rubric_version=self._rules.rubric_version))
            blocked = response.prompt_feedback and response.prompt_feedback.block_reason
            refusals = {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "IMAGE_SAFETY"}
            if ((blocked and blocked != "BLOCKED_REASON_UNSPECIFIED")
                    or any(c.finish_reason in refusals for c in candidates)
                    or any(rating.blocked for c in candidates for rating in c.safety_ratings or [])):
                return failure("PROVIDER_REFUSED")
            if len(candidates) == 1 and candidates[0].finish_reason in ("MAX_TOKENS", "CONTINUATION"):
                return failure("PROVIDER_OUTPUT_INVALID", True,
                               diagnostic=ProviderDiagnostic(category="output_truncated"))
            if len(candidates) != 1 or candidates[0].finish_reason != "STOP" or not text or unexpected:
                return failure("PROVIDER_OUTPUT_INVALID", True)
            payload = output_schema.model_validate_json(text, strict=True)
            return ProviderSuccess[output_schema](provider="gemini", model=request.model, payload=payload,
                                                  usage=usage, latency_seconds=max(0.0, self._clock() - started))
        except asyncio.CancelledError:
            raise
        except (TimeoutError, httpx.TimeoutException):
            return failure("DEADLINE_EXCEEDED", True)
        except httpx.TransportError as exc:
            return failure("PROVIDER_UNAVAILABLE", True, diagnostic=_transport_diagnostic(exc))
        except errors.APIError as exc:
            status = getattr(exc.response, "status_code", None)
            diagnostic = diagnostic_for_http(status if type(status) is int else exc.code)
            if exc.code in (408, 504):
                return failure("DEADLINE_EXCEEDED", True, retry_after=_retry_after(exc), diagnostic=diagnostic)
            if exc.code in (409, 429) or (isinstance(exc.code, int) and exc.code >= 500):
                return failure("PROVIDER_UNAVAILABLE", True, retry_after=_retry_after(exc), diagnostic=diagnostic)
            return failure("CONFIGURATION_ERROR", diagnostic=diagnostic)
        except (ValidationError, ValueError, TypeError, AttributeError, errors.UnknownApiResponseError):
            return failure("PROVIDER_OUTPUT_INVALID", True)
        except Exception:
            return failure("CONFIGURATION_ERROR")
