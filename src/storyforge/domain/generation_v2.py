"""V2 success payload; failure and accounting envelopes stay compatible."""

from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, model_validator

from storyforge.domain.generation import GenerationFailure, QualityReport, ResultBase
from storyforge.domain.story_v2 import BookConstraints, StoryV2


class GenerationSuccessV2(ResultBase):
    status: Literal["success"] = "success"
    story: StoryV2
    quality: QualityReport
    resolved_constraints: BookConstraints

    @model_validator(mode="after")
    def accepted_book(self) -> "GenerationSuccessV2":
        if not self.quality.passed or self.story.page_count != self.resolved_constraints.page_count:
            raise ValueError("V2 success requires an approved book matching resolved constraints")
        expected = self.resolved_constraints.target_ids or (None,) * self.story.page_count
        if tuple(page.target_id for page in self.story.pages) != expected:
            raise ValueError("Accepted target order must match resolved constraints")
        return self


GenerationResultV2 = Annotated[GenerationSuccessV2 | GenerationFailure, Field(discriminator="status")]
generation_result_v2_adapter = TypeAdapter(GenerationResultV2)
