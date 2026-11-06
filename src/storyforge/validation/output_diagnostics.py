"""Project validation errors onto bounded allowlists, never exception strings."""

from collections.abc import Iterable
from typing import TYPE_CHECKING, get_args

from pydantic import ValidationError

from storyforge.domain.diagnostics import ProviderDiagnostic
from storyforge.domain.output_validation import (
    OutputContractError, OutputField, OutputValidationIssue, SchemaRule,
)

if TYPE_CHECKING:
    from storyforge.domain.generation import AttemptRecord

_FIELDS = frozenset(get_args(OutputField))
_RULES = frozenset(get_args(SchemaRule))
_MAX_ISSUES = 8


def validation_diagnostic(error: ValueError) -> ProviderDiagnostic:
    if isinstance(error, OutputContractError):
        return ProviderDiagnostic(category="invalid_output", validation_issues=(error.issue,))
    if not isinstance(error, ValidationError):
        return ProviderDiagnostic(category="invalid_output", validation_issues=(
            OutputValidationIssue(code="unclassified_contract_violation"),))
    issues = []
    # ctx is inspected only for our typed error. Never serialize ctx/input/msg/url.
    errors = error.errors(include_input=False, include_context=True, include_url=False)
    for item in errors[:_MAX_ISSUES]:
        typed = item.get("ctx", {}).get("error")
        if isinstance(typed, OutputContractError):
            issues.append(typed.issue)
            continue
        path = tuple(part if type(part) is str and part in _FIELDS
                     else part if type(part) is int and 0 <= part <= 1000000
                     else "unknown" for part in item.get("loc", ())[:8])
        rule = item.get("type")
        issues.append(OutputValidationIssue(code="schema_validation", path=path,
                                            rule=rule if rule in _RULES else "other"))
    return ProviderDiagnostic(category="invalid_output", validation_issues=tuple(issues),
                              validation_issues_truncated=len(errors) > _MAX_ISSUES)


def export_validation_diagnostics(attempts: "Iterable[AttemptRecord]") -> list[dict[str, object]]:
    """Explicit evaluation-only export; normal result/API serialization omits it."""
    records: list[dict[str, object]] = []
    for attempt in attempts:
        diagnostic = attempt.provider_diagnostic
        if diagnostic and (diagnostic.validation_issues or diagnostic.validation_issues_truncated):
            records.append({"attempt_number": attempt.attempt_number, "stage": attempt.stage,
                "validation_issues": [issue.model_dump(mode="json") for issue in diagnostic.validation_issues],
                "validation_issues_truncated": diagnostic.validation_issues_truncated})
    return records
