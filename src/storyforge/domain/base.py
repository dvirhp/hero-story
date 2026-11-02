"""Strict immutable models and shared bounded scalar types."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Language = Literal["en", "he"]
NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]
Label = Annotated[str, StringConstraints(min_length=1, max_length=120, pattern=r"\S")]
Text = Annotated[str, StringConstraints(min_length=1, max_length=12000, pattern=r"\S")]
Seconds = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Money = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Contract(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
