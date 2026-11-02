"""One async Responses API invocation; recovery belongs exclusively to the graph."""

import asyncio
import math
import time
from collections.abc import Callable
from email.utils import parsedate_to_datetime

import httpx
from openai import APIConnectionError, APIResponseValidationError, APIStatusError, APITimeoutError, AsyncOpenAI
from pydantic import ValidationError

from storyforge.domain.generation import GenerationError, QualityReport, TokenUsage
from storyforge.llm.configuration import ModelCapabilities, OpenAIConfig
from storyforge.llm.protocol import LLMRequest, OutputT, ProviderFailure, ProviderSuccess
from storyforge.llm.schema import structured_schema
from storyforge.quality.gate import inspect_output_safety
from storyforge.quality.rules import DEFAULT_RULES, QualityRules


def create_sdk_client(config: OpenAIConfig, *, http_client: httpx.AsyncClient | None = None) -> AsyncOpenAI:
    """Construct only; no request or credential discovery. Caller owns cleanup."""
    return AsyncOpenAI(api_key=config.api_key.get_secret_value(), base_url="https://api.openai.com/v1",
                       max_retries=0, timeout=config.timeout_seconds,
                       http_client=http_client or httpx.AsyncClient(trust_env=False, follow_redirects=False))


def normalize_usage(raw: object) -> TokenUsage:
    if raw is None:
        return TokenUsage(source="unknown")
    try:
        return TokenUsage(
            source="reported", input_tokens=raw.input_tokens, output_tokens=raw.output_tokens,
            cached_input_tokens=getattr(getattr(raw, "input_tokens_details", None), "cached_tokens", None),
            reasoning_output_tokens=getattr(getattr(raw, "output_tokens_details", None), "reasoning_tokens", None),
        )
    except (ValidationError, AttributeError):
        return TokenUsage(source="unknown")


def _retry_after(headers: httpx.Headers) -> float | None:
    value = headers.get("retry-after")
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            seconds = parsedate_to_datetime(value).timestamp() - time.time()
        except (ValueError, TypeError, OverflowError):
            return None
    return max(0.0, seconds) if math.isfinite(seconds) else None


class OpenAIProvider:
    provider_name = "openai"

    def __init__(
        self, client: AsyncOpenAI, config: OpenAIConfig, capabilities: ModelCapabilities | tuple[ModelCapabilities, ...], *,
        rules: QualityRules = DEFAULT_RULES, clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if client.max_retries != 0:
            raise ValueError("SDK retries must be disabled before constructing the adapter")
        self._client = client
        self._config, self._rules, self._clock = config, rules, clock
        entries = (capabilities,) if isinstance(capabilities, ModelCapabilities) else capabilities
        self._capabilities = {entry.model: entry for entry in entries}
        if len(self._capabilities) != len(entries):
            raise ValueError("Duplicate model capabilities")

    async def generate(
        self, request: LLMRequest, output_schema: type[OutputT],
    ) -> ProviderSuccess[OutputT] | ProviderFailure:
        started = self._clock()
        usage = TokenUsage(source="unknown")

        def failure(code: str, retryable: bool = False, *, quality=None, retry_after=None) -> ProviderFailure:
            messages = {
                "CONFIGURATION_ERROR": "Provider credentials, model or request configuration is invalid",
                "PROVIDER_UNAVAILABLE": "Provider temporarily unavailable",
                "DEADLINE_EXCEEDED": "Provider attempt timed out",
                "PROVIDER_OUTPUT_INVALID": "Provider output did not match the structured contract",
                "PROVIDER_REFUSED": "Provider declined to produce a story",
                "POLICY_REJECTED": "Provider output contains prohibited content or controls",
            }
            return ProviderFailure(provider="openai", model=request.model, usage=usage,
                                   latency_seconds=max(0.0, self._clock() - started), quality=quality,
                                   retry_after_seconds=retry_after,
                                   error=GenerationError(code=code, stage=request.stage, retryable=retryable,
                                                         message=messages[code]))

        capabilities = self._capabilities.get(request.model)
        if capabilities is None or request.max_output_tokens > capabilities.max_output_tokens:
            return failure("CONFIGURATION_ERROR")
        try:
            response = await self._client.responses.create(
                model=request.model, instructions=request.instructions,
                input=[{"role": "user", "content": request.input_json}],
                text={"format": {"type": "json_schema", "name": output_schema.__name__,
                                 "schema": structured_schema(output_schema), "strict": True}},
                max_output_tokens=request.max_output_tokens,
                timeout=min(request.remaining_seconds, self._config.timeout_seconds),
                store=False, background=False, stream=False, tools=[],
            )
            usage = normalize_usage(response.usage)
            pieces: list[str] = []
            refused = False
            unexpected = False
            for item in response.output:
                if item.type == "reasoning":
                    continue  # Never expose reasoning data.
                if item.type != "message":
                    unexpected = True
                    continue
                for part in item.content:
                    if part.type == "refusal":
                        refused = True
                    elif part.type == "output_text" and isinstance(part.text, str):
                        pieces.append(part.text)
                    else:
                        unexpected = True
            text = "".join(pieces)
            unsafe = inspect_output_safety(text, self._rules)
            if unsafe:
                report = QualityReport(passed=False, issues=unsafe, check_version=self._rules.version,
                                       rubric_version=self._rules.rubric_version)
                return failure("POLICY_REJECTED", quality=report)
            if refused or (response.status == "incomplete"
                           and getattr(response.incomplete_details, "reason", None) == "content_filter"):
                return failure("PROVIDER_REFUSED")
            if response.error is not None:
                transient = response.error.code in ("server_error", "rate_limit_exceeded")
                return failure("PROVIDER_UNAVAILABLE" if transient else "CONFIGURATION_ERROR", transient)
            if response.status != "completed" or not text or unexpected:
                return failure("PROVIDER_OUTPUT_INVALID", True)
            payload = output_schema.model_validate_json(text, strict=True)
            return ProviderSuccess[output_schema](provider="openai", model=request.model, payload=payload,
                                                  usage=usage, latency_seconds=max(0.0, self._clock() - started))
        except asyncio.CancelledError:
            raise
        except APITimeoutError:
            return failure("DEADLINE_EXCEEDED", True)
        except APIConnectionError:
            return failure("PROVIDER_UNAVAILABLE", True)
        except APIResponseValidationError:
            return failure("PROVIDER_OUTPUT_INVALID", True)
        except APIStatusError as exc:
            if exc.status_code == 408:
                return failure("DEADLINE_EXCEEDED", True)
            if exc.status_code in (409, 429) or exc.status_code >= 500:
                return failure("PROVIDER_UNAVAILABLE", True, retry_after=_retry_after(exc.response.headers))
            return failure("CONFIGURATION_ERROR")
        except (ValidationError, ValueError, AttributeError, TypeError):
            return failure("PROVIDER_OUTPUT_INVALID", True)
        except Exception:
            return failure("CONFIGURATION_ERROR")
