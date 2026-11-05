"""Fixed internal errors and strict revalidation without private validation inputs."""

from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class InvalidBook(ValueError):
    def __init__(self) -> None:
        super().__init__("BOOK_INPUT_INVALID")


class BookConflict(ValueError):
    def __init__(self) -> None:
        super().__init__("BOOK_REVISION_OR_STATE_CONFLICT")


def checked(model: type[T], value: T) -> T:
    try:
        return model.model_validate_json(value.model_dump_json())
    except (ValidationError, ValueError, AttributeError, TypeError):
        raise InvalidBook() from None
