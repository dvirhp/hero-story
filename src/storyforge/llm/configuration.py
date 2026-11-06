"""Explicit provider credentials/capabilities; no environment reads or live probes."""

from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator

from storyforge.domain.base import Contract, Label, PositiveInt


class ProviderCredentials(Contract):
    api_key: SecretStr = Field(exclude=True, repr=False)
    timeout_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)]

    @field_validator("api_key")
    @classmethod
    def nonempty_key(cls, key: SecretStr) -> SecretStr:
        if not key.get_secret_value().strip():
            raise ValueError("An explicitly supplied API key is required")
        return key


class OpenAIConfig(ProviderCredentials):
    """Explicit OpenAI credentials."""


class GeminiConfig(ProviderCredentials):
    """Explicit Gemini Developer API credentials, never ambient SDK discovery."""


class ModelCapabilities(Contract):
    model: Label
    version: Label
    context_tokens: PositiveInt
    max_output_tokens: PositiveInt
    input_overhead_tokens: PositiveInt
    structured_outputs: Literal[True]
    token_bound_version: Label = "openai-utf8-upper-v1"
    # Explicit server-reviewed model settings; None preserves older runtimes.
    gemini_thinking_level: Literal["minimal", "low", "medium", "high"] | None = None
    openai_reasoning_effort: Literal["none", "minimal", "low", "medium", "high"] | None = None
