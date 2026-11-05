"""Pure B1 projection and admission. Synthetic accepted sources, no provider I/O."""

import json
from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from uuid import UUID

import pytest

from storyforge.config import AppSettings
from storyforge.development.v2 import load_profiles_v2
from storyforge.domain.generation import GenerationError, GenerationFailure, UsageSummary
from storyforge.domain.generation_v2 import GenerationSuccessV2
from storyforge.domain.story_v2 import StoryRequestV2, StoryV2
from storyforge.llm.fixtures_v2 import fixture_steps_v2
from storyforge.projection.capacity import CapacityPolicy, ProjectionError, canonical_json_bytes
from storyforge.projection.contracts import AITextBookProjection, ProjectionContext
from storyforge.projection.service import admit_projection, project_accepted_story, validate_projected_book
from storyforge.quality.gate import assess_story
from storyforge.validation.normalization_v2 import normalize_v2
from storyforge.validation.page_policy import PagePolicy

SETTINGS = AppSettings(planner_output_tokens=5000, writer_output_tokens=20000, max_input_tokens=64000)


def context(**changes):
    return ProjectionContext(**dict(
        operation_id=UUID(int=1), generation_id=UUID(int=2), book_id=UUID(int=3),
        source_request_id="synthetic-request", operation_owner_id=UUID(int=4),
        source_owner_id=UUID(int=4), book_owner_id=UUID(int=4), authorized_owner_ids=(UUID(int=4),),
        created_at=datetime(2026, 11, 5, tzinfo=timezone.utc),
    ) | changes)


def source(language="en", age=36, pages=2, raw=None):
    request = StoryRequestV2.model_validate_json(json.dumps(raw)) if raw else StoryRequestV2(
        language=language, age_months=age, page_count=pages,
        display_name="אור" if language == "he" else "Or", theme="לילה" if language == "he" else "Night")
    brief = normalize_v2(request, load_profiles_v2(), settings=SETTINGS)
    story = StoryV2.model_validate_json(fixture_steps_v2(brief)[1].response_json)
    report = assess_story(story, brief)
    assert report.passed
    return brief, GenerationSuccessV2(request_id="synthetic-request", usage=UsageSummary(),
                                     total_latency_seconds=0.0, story=story,
                                     quality=report, resolved_constraints=brief.constraints)


def project(result, brief, **changes):
    ids = count(100)
    return project_accepted_story(result, brief, context(),
                                  page_id_factory=lambda: UUID(int=next(ids)), **changes)


@pytest.mark.parametrize("language", ["he", "en"])
@pytest.mark.parametrize("age", [0, 2, 3, 11, 12, 35, 36, 71, 72, 1000000])
@pytest.mark.parametrize("pages", [1, 6, 27, 32])
def test_exact_lossless_initial_projection_crosses_age_and_length(language, age, pages):
    brief, result = source(language, age, pages)
    admission = admit_projection(brief, context())
    book = project(result, brief)
    assert book.page_count == len(book.pages) == pages
    assert book.direction == ("rtl" if language == "he" else "ltr")
    assert book.origin.generation_id == context().generation_id
    assert len(canonical_json_bytes(book)) <= admission.book_upper_bytes
    for old, new in zip(result.story.pages, book.pages, strict=True):
        assert new.position == old.page_number
        assert new.source_page_key == old.page_id and new.source_target_id == old.target_id
        assert new.document.blocks[0].sentence_units == old.sentence_units
        assert str(new.page_id) != old.page_id and new.asset_bindings == ()
        assert len(canonical_json_bytes(new.document)) <= admission.document_upper_bytes
    assert AITextBookProjection.model_validate_json(canonical_json_bytes(book)) == book


def test_roy_target_provenance_and_supplied_title_are_preserved():
    raw = json.loads((Path(__file__).resolve().parents[1] / "docs/examples/roy-alphabet-request.v2.he.json")
                     .read_text(encoding="utf-8"))
    brief, result = source(raw=raw)
    book = project(result, brief)
    assert book.title == raw["requested_title"]
    assert book.page_count == 27
    assert [p.source_target_id for p in book.pages] == [t["target_id"] for t in raw["structure"]["targets"]]
    assert len({page.page_id for page in book.pages}) == 27
    # No claim of educational or literary correctness from this synthetic text.


@pytest.mark.parametrize("mutation,code", [
    ("failed", "SOURCE_NOT_ACCEPTED"), ("short", "SOURCE_NOT_ACCEPTED"),
    ("order", "SOURCE_NOT_ACCEPTED"), ("duplicate_source", "SOURCE_NOT_ACCEPTED"),
    ("density", "SOURCE_NOT_ACCEPTED"), ("missing_name", "SOURCE_NOT_ACCEPTED"),
    ("quality", "SOURCE_NOT_ACCEPTED"), ("request_id", "SOURCE_MISMATCH"),
    ("constraints", "SOURCE_MISMATCH"),
])
def test_rejects_failed_incomplete_forged_or_uncorrelated_sources(mutation, code):
    brief, result = source()
    if mutation == "failed":
        result = GenerationFailure(request_id="synthetic-request", usage=UsageSummary(), total_latency_seconds=0.0,
            error=GenerationError(code="PROVIDER_UNAVAILABLE", stage="writer", retryable=False, message="private-canary"))
    elif mutation == "request_id":
        result = result.model_copy(update={"request_id": "different-request"})
    elif mutation == "quality":
        result = result.model_copy(update={"quality": result.quality.model_copy(update={"passed": False})})
    elif mutation == "constraints":
        hard = brief.constraints
        words = hard.words_per_page.model_copy(update={"minimum": hard.words_per_page.minimum - 1})
        totals = hard.total_words.model_copy(update={"minimum": words.minimum * hard.page_count})
        result = result.model_copy(update={"resolved_constraints": hard.model_copy(
            update={"words_per_page": words, "total_words": totals})})
    else:
        raw = result.story.model_dump(mode="json")
        if mutation == "short":
            raw["pages"].pop(); raw["page_count"] -= 1
        elif mutation == "order":
            raw["pages"].reverse()
        elif mutation == "duplicate_source":
            raw["pages"][1]["page_id"] = raw["pages"][0]["page_id"]
        elif mutation == "density":
            raw["pages"][0]["sentence_units"] = ["Or"]
        else:
            for page in raw["pages"]:
                page["sentence_units"] = [u.replace("Or", "Someone") for u in page["sentence_units"]]
        # Deliberately bypass construction to verify the boundary revalidates.
        result = result.model_copy(update={"story": result.story.model_copy(update=raw)})
    with pytest.raises(ProjectionError) as failure:
        project(result, brief)
    assert failure.value.code == code
    assert "private-canary" not in str(failure.value)


@pytest.mark.parametrize("field", ["check_version", "rubric_version"])
def test_quality_version_evidence_must_match_current_deterministic_rules(field):
    brief, result = source()
    forged = result.quality.model_copy(update={field: "forged-v999"})
    result = result.model_copy(update={"quality": forged})
    with pytest.raises(ProjectionError, match="SOURCE_NOT_ACCEPTED"):
        project(result, brief)


@pytest.mark.parametrize("change", [
    {"source_owner_id": UUID(int=9)}, {"book_owner_id": UUID(int=9)},
    {"authorized_owner_ids": (UUID(int=9),)},
])
def test_verified_scope_and_all_issuance_owners_must_match(change):
    brief, result = source()
    with pytest.raises(ProjectionError, match="UNAUTHORIZED"):
        project_accepted_story(result, brief, context(**change))


@pytest.mark.parametrize("factory", [lambda: UUID(int=100), lambda: "not-a-uuid"])
def test_rejects_duplicate_or_invalid_new_page_ids(factory):
    brief, result = source()
    with pytest.raises(ProjectionError, match="IDENTITY_CONFLICT"):
        project_accepted_story(result, brief, context(), page_id_factory=factory)


def test_canonical_uuid_must_not_reuse_source_uuid():
    brief, result = source(pages=1)
    story = result.story.model_copy(update={"pages": (result.story.pages[0].model_copy(
        update={"page_id": str(UUID(int=100))}),)})
    result = result.model_copy(update={"story": story})
    with pytest.raises(ProjectionError, match="IDENTITY_CONFLICT"):
        project(result, brief)


def test_exact_actual_byte_boundaries_and_configured_product_limits():
    brief, result = source(language="he")
    book = project(result, brief)
    doc_bytes = len(canonical_json_bytes(book.pages[0].document))
    book_bytes = len(canonical_json_bytes(book))
    assert validate_projected_book(book, CapacityPolicy(maximum_document_bytes=doc_bytes,
                                                      maximum_book_bytes=book_bytes)) == book
    for changes in [dict(maximum_document_bytes=doc_bytes - 1), dict(maximum_book_bytes=book_bytes - 1),
                    dict(maximum_story_pages=1), dict(maximum_sentence_units=1, maximum_unit_code_points=4)]:
        with pytest.raises(ProjectionError, match="CAPACITY_EXCEEDED"):
            validate_projected_book(book, CapacityPolicy(**changes))


@pytest.mark.parametrize("changes", [dict(maximum_story_pages=1), dict(maximum_sentence_units=10),
    dict(maximum_unit_code_points=399), dict(maximum_title_code_points=119),
    dict(maximum_document_bytes=1000), dict(maximum_book_bytes=1000)])
def test_conservative_admission_rejects_without_calling_any_provider(changes):
    brief, _ = source()
    with pytest.raises(ProjectionError, match="CAPACITY_EXCEEDED"):
        admit_projection(brief, context(), CapacityPolicy(**changes))


@pytest.mark.parametrize("unit", ["a" * 400, "א" * 400, "😀" * 400, '"' * 400, "\\" * 400, "\t" * 399 + "x"])
def test_byte_proof_covers_utf8_and_escaping_at_current_maximum_density(unit):
    brief, result = source(age=120, pages=32)
    # Actual capacity validation does not assert that this is a good manuscript.
    book = project(result, brief)
    raw = book.model_dump(mode="json")
    for page in raw["pages"]:
        page["document"]["blocks"][0]["sentence_units"] = [unit] * 70
        page["source_page_key"] = "😀" * 118 + str(page["position"])
        page["source_target_id"] = "😀" * 120
    raw["title"] = "😀" * 120
    bound = admit_projection(brief, context())
    candidate = AITextBookProjection.model_validate_json(json.dumps(raw, ensure_ascii=True))
    assert validate_projected_book(candidate)
    assert len(canonical_json_bytes(candidate)) <= bound.book_upper_bytes
    assert len(canonical_json_bytes(candidate.pages[0].document)) <= bound.document_upper_bytes


def test_v2_schema_is_unchanged_and_does_not_gain_projection_fields():
    assert "maximum_story_pages" not in StoryRequestV2.model_fields
    assert "book_id" not in StoryV2.model_fields
    assert "maxItems" not in StoryV2.model_json_schema()["$defs"]["StoryPageV2"]["properties"]["sentence_units"]


@pytest.mark.parametrize("change", [{"revision": True}, {"private_extra": "canary"},
                                   {"page_count": True}, {"direction": "rtl"}])
def test_revalidation_rejects_typed_projection_construction_shortcuts(change):
    brief, result = source()
    book = project(result, brief).model_copy(update=change)
    with pytest.raises(ProjectionError, match="INPUT_INVALID"):
        validate_projected_book(book)


def test_context_and_config_revalidation_rejects_model_copy_bypasses():
    brief, _ = source()
    for identity, policy in [(context().model_copy(update={"extra": "canary"}), CapacityPolicy()),
                             (context(), CapacityPolicy().model_copy(update={"maximum_story_pages": True}))]:
        with pytest.raises(ProjectionError, match="INPUT_INVALID"):
            admit_projection(brief, identity, policy)


@pytest.mark.parametrize("language", ["he", "en"])
@pytest.mark.parametrize("age", [0, 3, 12, 36, 72])
def test_light_density_is_not_replaced_with_a_universal_length(language, age):
    brief, result = source(raw=dict(language=language, age_months=age, page_count=2,
        display_name="אור" if language == "he" else "Or", theme="Night", text_density="light"))
    book = project(result, brief)
    assert book.pages[0].document.blocks[0].sentence_units == result.story.pages[0].sentence_units
    assert admit_projection(brief, context()).maximum_units_per_page == brief.constraints.words_per_page.maximum


def test_explicit_title_has_exact_admission_bound_and_no_rewriting():
    brief, result = source(raw=dict(language="he", age_months=36, page_count=1,
        display_name="אור", theme="Night", requested_title="שָׁלוֹם 😀"))
    policy = CapacityPolicy(maximum_title_code_points=len(brief.request.requested_title))
    assert project(result, brief, policy=policy).title == brief.request.requested_title


def test_product_limit_can_be_raised_in_isolated_offline_policy_without_graph_edits():
    request = StoryRequestV2(language="en", age_months=0, page_count=33, display_name="Or", theme="Night")
    brief = normalize_v2(request, load_profiles_v2(), settings=SETTINGS,
                         page_policy=PagePolicy(maximum_pages=33))
    story = StoryV2.model_validate_json(fixture_steps_v2(brief)[1].response_json)
    result = GenerationSuccessV2(request_id="synthetic-request", usage=UsageSummary(), total_latency_seconds=0.0,
                                story=story, quality=assess_story(story, brief), resolved_constraints=brief.constraints)
    with pytest.raises(ProjectionError, match="CAPACITY_EXCEEDED"):
        admit_projection(brief, context())
    assert project(result, brief, policy=CapacityPolicy(maximum_story_pages=33)).page_count == 33
