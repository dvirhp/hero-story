"""Allowlisted failure metadata; no provider SDK or free-form diagnostic text."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from storyforge.domain.base import Contract
from storyforge.domain.output_validation import OutputValidationIssue

FailureCategory = Literal[
    "invalid_request", "authentication", "permission_denied", "not_found", "conflict",
    "rate_or_quota_limit", "server_error", "connection_error", "dns_error", "tls_error",
    "transport_error", "timeout", "configuration_error", "invalid_output", "refused",
    "policy_rejected", "cancelled", "unknown", "output_truncated",
]


class ProviderDiagnostic(Contract):
    model_config = ConfigDict(revalidate_instances="always")
    category: FailureCategory
    upstream_http_status: Annotated[int, Field(ge=100, le=599)] | None = None
    # Internal evaluation detail only: excluded from production JSON/OpenAPI.
    validation_issues: Annotated[tuple[OutputValidationIssue, ...], Field(max_length=8, exclude=True)] = ()
    validation_issues_truncated: bool = Field(default=False, exclude=True)


def diagnostic_for_code(code: str) -> ProviderDiagnostic:
    category = {
        "CONFIGURATION_ERROR": "configuration_error", "PROVIDER_OUTPUT_INVALID": "invalid_output",
        "PROVIDER_REFUSED": "refused", "POLICY_REJECTED": "policy_rejected",
        "DEADLINE_EXCEEDED": "timeout", "CANCELLED": "cancelled",
    }.get(code, "unknown")
    return ProviderDiagnostic(category=category)


def diagnostic_for_http(status: object) -> ProviderDiagnostic:
    if type(status) is not int or not 100 <= status <= 599:
        return ProviderDiagnostic(category="unknown")
    category = {
        400: "invalid_request", 401: "authentication", 403: "permission_denied", 404: "not_found",
        408: "timeout", 409: "conflict", 429: "rate_or_quota_limit", 504: "timeout",
    }.get(status, "server_error" if status >= 500 else "configuration_error")
    return ProviderDiagnostic(category=category, upstream_http_status=status)


StopReason = Literal[
    "attempt_capacity_exhausted", "token_budget_exhausted", "cost_budget_exhausted",
    "input_capacity_exceeded", "resource_capacity_exhausted",
    "deadline_exceeded", "cancelled", "provider_failure", "quality_rejected",
    "input_rejected", "configuration_error",
]


def stop_reason_for_code(code: str) -> StopReason:
    return {
        "BUDGET_EXCEEDED": "resource_capacity_exhausted", "DEADLINE_EXCEEDED": "deadline_exceeded",
        "CANCELLED": "cancelled", "QUALITY_REJECTED": "quality_rejected",
        "INPUT_INVALID": "input_rejected", "CONFIGURATION_ERROR": "configuration_error",
    }.get(code, "provider_failure")
