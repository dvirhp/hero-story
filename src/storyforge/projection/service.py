"""Pure admission and accepted-source mapping; never starts an engine/provider."""

from collections.abc import Callable
from uuid import UUID, uuid4

from pydantic import ValidationError

from storyforge.domain.generation_v2 import GenerationSuccessV2
from storyforge.domain.base import PositiveInt
from storyforge.domain.story_v2 import NormalizedBriefV2
from storyforge.projection.capacity import CapacityPolicy, ProjectionError, canonical_json_bytes, json_bytes
from storyforge.projection.contracts import (
    AIOrigin, AITextBlock, AITextBookPage, AITextBookProjection,
    AITextPageDocument, ProjectionContext, ProjectionContract,
)
from storyforge.quality.gate import assess_story
from storyforge.quality.rules import DEFAULT_RULES, QualityRules


class ProjectionAdmission(ProjectionContract):
    policy: CapacityPolicy
    maximum_units_per_page: PositiveInt
    document_upper_bytes: PositiveInt
    book_upper_bytes: PositiveInt


def _inputs(brief, context, policy):
    try:
        if (not isinstance(brief, NormalizedBriefV2) or not isinstance(context, ProjectionContext)
                or not isinstance(policy, CapacityPolicy)):
            raise ValueError()
        brief = NormalizedBriefV2.model_validate_json(brief.model_dump_json(warnings=False))
        context = ProjectionContext.model_validate(context)
        policy = CapacityPolicy.model_validate(policy)
    except (ValidationError, ValueError, TypeError, AttributeError, UnicodeError):
        raise ProjectionError("INPUT_INVALID") from None
    if (context.operation_owner_id != context.source_owner_id
            or context.operation_owner_id != context.book_owner_id
            or context.operation_owner_id not in context.authorized_owner_ids):
        raise ProjectionError("UNAUTHORIZED")
    return brief, context, policy


def _header(brief: NormalizedBriefV2, context: ProjectionContext, title: str) -> dict:
    timestamp = context.created_at.isoformat().replace("+00:00", "Z")
    return dict(schema_version="1", book_id=str(context.book_id), creation_mode="AI_GENERATED",
                state="draft", revision=1, title=title, language=brief.request.language,
                direction="rtl" if brief.request.language == "he" else "ltr",
                page_count=brief.request.page_count, created_at=timestamp, updated_at=timestamp,
                origin=AIOrigin(generation_id=context.generation_id).model_dump(mode="json"),
                personalization=None, finalized_at=None, archived_at=None, pages=[])


def admit_projection(
    brief: NormalizedBriefV2, context: ProjectionContext, policy: CapacityPolicy = CapacityPolicy(),
) -> ProjectionAdmission:
    """Prove every conforming source fits this representation, before generation.

    This is canonical admission only, not provider, monetary or token admission.
    """
    brief, context, policy = _inputs(brief, context, policy)
    n, hard = brief.request.page_count, brief.constraints
    units = hard.words_per_page.maximum  # Each nonempty unit contains >=1 split word.
    if hard.sentence_units_per_page:
        units = min(units, hard.sentence_units_per_page.maximum)
    # Existing Writer schema permits 400 characters/unit and 120/title. A lower
    # policy cannot silently narrow that contract. An explicit title is known.
    title = brief.request.requested_title
    if (n > policy.maximum_story_pages or units > policy.maximum_sentence_units
            or policy.maximum_unit_code_points < 400
            or (len(title) if title is not None else 120) > policy.maximum_title_code_points):
        raise ProjectionError("CAPACITY_EXCEEDED")

    language = brief.request.language
    empty_document = dict(schema_version="1", layout={"preset": "text-only-v1"}, blocks=[
        dict(kind="text", block_id="body", language=language,
             direction="rtl" if language == "he" else "ltr", style="body", sentence_units=[])])
    # A JSON code point occupies <=6 bytes with ensure_ascii=False (escaped C0
    # controls are 6; astral code points are 4). Surrogates are rejected separately.
    unit_bytes = units * (2 + 6 * 400) + max(0, units - 1)
    document_bound = len(json_bytes(empty_document)) + unit_bytes
    page_template = dict(page_id=str(UUID(int=0)), position=n, document=empty_document,
                         asset_bindings=[], source_page_key="", source_target_id="")
    # Unknown source keys/target IDs are bounded Labels, <=120 code points each.
    page_bound = len(json_bytes(page_template)) + unit_bytes + 2 * 6 * 120
    header = _header(brief, context, title or "")
    title_bytes = 0 if title is not None else 6 * 120
    book_bound = len(json_bytes(header)) + title_bytes + n * page_bound + max(0, n - 1)
    if document_bound > policy.maximum_document_bytes or book_bound > policy.maximum_book_bytes:
        raise ProjectionError("CAPACITY_EXCEEDED")
    return ProjectionAdmission(policy=policy, maximum_units_per_page=units,
                               document_upper_bytes=document_bound, book_upper_bytes=book_bound)


def validate_projected_book(
    book: AITextBookProjection, policy: CapacityPolicy = CapacityPolicy(),
) -> AITextBookProjection:
    """Revalidate actual structure and exact bytes; this is not source approval."""
    try:
        if not isinstance(book, AITextBookProjection) or not isinstance(policy, CapacityPolicy):
            raise ValueError()
        book = AITextBookProjection.model_validate(book)
        policy = CapacityPolicy.model_validate(policy)
        if (book.page_count > policy.maximum_story_pages
                or len(book.title) > policy.maximum_title_code_points):
            raise ProjectionError("CAPACITY_EXCEEDED")
        for page in book.pages:
            units = page.document.blocks[0].sentence_units
            if (len(units) > policy.maximum_sentence_units
                    or any(len(unit) > policy.maximum_unit_code_points for unit in units)
                    or len(canonical_json_bytes(page.document)) > policy.maximum_document_bytes):
                raise ProjectionError("CAPACITY_EXCEEDED")
        if len(canonical_json_bytes(book)) > policy.maximum_book_bytes:
            raise ProjectionError("CAPACITY_EXCEEDED")
    except ProjectionError:
        raise
    except (ValidationError, ValueError, TypeError, AttributeError, UnicodeError):
        raise ProjectionError("INPUT_INVALID") from None
    return book


def project_accepted_story(
    result: GenerationSuccessV2, brief: NormalizedBriefV2, context: ProjectionContext,
    policy: CapacityPolicy = CapacityPolicy(), *, page_id_factory: Callable[[], UUID] = uuid4,
    rules: QualityRules = DEFAULT_RULES,
) -> AITextBookProjection:
    """Lossless initial projection; trusted backend supplies verified identity scope.

    An accepted model is not cryptographic provenance. This function rechecks
    current injected deterministic rules, never literary quality or authentication.
    """
    brief, context, policy = _inputs(brief, context, policy)
    admit_projection(brief, context, policy)
    try:
        if not isinstance(result, GenerationSuccessV2):
            raise ValueError()
        result = GenerationSuccessV2.model_validate_json(result.model_dump_json(warnings=False))
        result.story.validate_for(brief)
    except (ValidationError, ValueError, TypeError, AttributeError, UnicodeError):
        raise ProjectionError("SOURCE_NOT_ACCEPTED") from None
    if result.request_id != context.source_request_id or result.resolved_constraints != brief.constraints:
        raise ProjectionError("SOURCE_MISMATCH")
    report = assess_story(result.story, brief, rules)
    if (not report.passed or report.check_version != result.quality.check_version
            or report.rubric_version != result.quality.rubric_version):
        raise ProjectionError("SOURCE_NOT_ACCEPTED")
    pages = []
    ids = set()
    source_keys = {page.page_id for page in result.story.pages}
    for source in result.story.pages:
        page_id = page_id_factory()
        if (not isinstance(page_id, UUID) or page_id in ids or str(page_id) in source_keys):
            raise ProjectionError("IDENTITY_CONFLICT")
        ids.add(page_id)
        pages.append(AITextBookPage(
            page_id=page_id, position=source.page_number, source_page_key=source.page_id,
            source_target_id=source.target_id,
            document=AITextPageDocument(blocks=(AITextBlock(
                language=result.story.language, direction=result.story.direction,
                sentence_units=source.sentence_units),)),
        ))
    header = _header(brief, context, result.story.title)
    # JSON-mode validation accepts arrays/UUID/timestamps without Python coercion.
    header["pages"] = [page.model_dump(mode="json") for page in pages]
    book = AITextBookProjection.model_validate_json(json_bytes(header))
    return validate_projected_book(book, policy)
