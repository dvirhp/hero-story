"""Closed, text-free output violations; domain contracts never expose inputs."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from storyforge.domain.base import Contract

OutputField = Literal[
    "pages", "sentence_units", "page_count", "page_number", "page_id", "target_id",
    "title", "language", "direction", "profile_id", "profile_version", "protagonist",
    "strategy", "plot", "goal", "obstacle_or_choices", "resolution", "intent",
    "progression", "schema_version", "title_concept", "text", "unknown",
]
OutputPath = Annotated[tuple[OutputField | Annotated[int, Field(ge=0, le=1000000)], ...], Field(max_length=8)]
OutputViolation = Literal[
    "schema_validation", "unclassified_contract_violation", "page_order", "duplicate_page_id",
    "direction_mismatch", "plot_missing", "plan_context_mismatch", "declared_page_count",
    "page_count_mismatch", "language_mismatch", "profile_mismatch", "target_sequence_mismatch",
    "title_mismatch", "sentence_unit_count", "page_word_count", "total_word_count",
    "rewrite_page_ids_changed", "unexpected_response_shape",
]
SchemaRule = Literal[
    "json_invalid", "missing", "extra_forbidden", "string_type", "int_type", "tuple_type",
    "list_type", "dict_type", "model_type", "literal_error", "string_too_long", "string_too_short",
    "too_long", "too_short", "string_pattern_mismatch", "value_error", "other",
]
Count = Annotated[int, Field(ge=0, le=1000000)]


class OutputValidationIssue(Contract):
    model_config = ConfigDict(revalidate_instances="always")
    code: OutputViolation
    path: OutputPath = ()  # Zero-based array indices, never caller-supplied IDs/keys.
    rule: SchemaRule | None = None
    observed_count: Count | None = None
    minimum_count: Count | None = None
    maximum_count: Count | None = None


class OutputContractError(ValueError):
    """Typed local constraint failure, compatible with existing ValueError callers."""

    def __init__(self, code: OutputViolation, *, path: OutputPath = (),
                 observed_count: int | None = None, minimum_count: int | None = None,
                 maximum_count: int | None = None) -> None:
        def bounded(value):
            return value if type(value) is int and 0 <= value <= 1000000 else None
        self.issue = OutputValidationIssue(code=code, path=path,
            observed_count=bounded(observed_count), minimum_count=bounded(minimum_count),
            maximum_count=bounded(maximum_count))
        super().__init__("Output did not match the validated contract")
