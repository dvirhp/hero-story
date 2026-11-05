# Phase B1: offline canonical AI text projection

Implemented only the user-approved initial text projection. No API, graph,
provider, database, migrations, auth, jobs, frontend or runtime configuration is
changed. No provider call is made by projection/admission. See the approved scope
in [final reconciliation](AI_BACKEND_FINAL_RECONCILIATION.md).

## Modules and ownership

- `projection/contracts.py`: immutable, strict initial AI variants of Agent 3's
  canonical shape: AITextBlock, AITextPageDocument, AITextBookPage and
  AITextBookProjection. Exactly one body block/text-only-v1; empty asset bindings;
  initial AI_GENERATED/draft/revision 1. No editable or multimode aggregate.
- `projection/capacity.py`: server-owned CapacityPolicy version
  ai-text-document-v1, sanitized ProjectionError and exact compact UTF-8 serializer.
- `projection/service.py`: admit_projection, project_accepted_story and
  validate_projected_book; no engine execution or persistence dependency.

Agent 3 still owns the complete Book/PageDocument domain, product DTOs, store and
eventual v3 adapters. These reviewed initial AI variants match its documented
fields; they do not implement or supersede its generic authoring model. No v3
HTTP DTO, operation receipt, session model or product source snapshot is invented.
Agent 3 must validate this projection against its eventual shared model and reuse
or relocate these types during approved integration, not maintain two editable
Book sources. Its broader persistence milestone is outside this B1 authorization.

## Policy and exact bytes

Default product maximum: 32 story pages, configurable independently of age and
provider sizing. Technical ceilings: title 120 code points, 128 nonempty units/page,
400 code points/unit, 262144 bytes/PageDocument and 16777216 bytes/complete projected
BookDetail. Policy can tighten technical ceilings, not exceed them. Exactly one
text block is a structural rule, not an age-dependent writing target. Current
profile density/sentence guidance and supplied hard entry counts remain unchanged.

Serialization includes all defined fields, nulls, empty bindings, provenance,
timestamps, UUIDs and Book/page wrappers: ensure_ascii=False, compact separators,
UTF-8, no NaN. Byte caps are inclusive. Strings retain exact logical Unicode,
niqqud, punctuation, spacing and sentence-unit boundaries. Existing prohibited
controls/lone surrogates are rejected; text is never normalized or truncated.

admit_projection(brief, context, policy) proves conservative finite bounds using
existing 120-character title/Label and 400-character unit contracts. Unit upper
bound is min(profile hard maximum words, explicit maximum entries if supplied),
because every nonempty entry has at least one whitespace word. Bound JSON strings
at six bytes/code point plus exact wrapper lengths. Admission is conservative:
it can reject a configuration even if one particular short output would fit.
Lowering a unit/title ceiling cannot silently narrow the unchanged Writer schema;
reject admission if compliance cannot be proven (an explicit requested title is
known). This is separate from provider/token/cost admission and is not wired into
existing generation routes under B1.

validate_projected_book revalidates typed objects and computes actual document
and complete Book bytes. It certifies representation only, not accepted source,
authorization, fluency or safety. A Pydantic object alone is not publication proof.

## Accepted source and trusted context

project_accepted_story accepts GenerationSuccessV2 plus its frozen NormalizedBriefV2
and a private ProjectionContext. It revalidates source structure, contextual
constraints, correlation ID and passing deterministic quality/version evidence,
then reruns the injected deterministic gate. Failed/partial/rejected/oversized
sources cannot be projected. This does not detect all prose/education defects.

Context is trusted composition input, not a new client DTO or authentication
implementation. Backend must supply verified authorized issuance namespaces,
matching immutable operation/source/Book owner IDs, source correlation, resource
UUIDs and UTC timestamp. This layer checks those assertions consistently; it
cannot prove credentials or cryptographic provenance of a source. Namespace claims
can authorize the original issuance owner without rewriting it. Actor IDs never
appear in the projected Book. Unauthorized/mismatched context is rejected with a
fixed error category, never private input details.

Each canonical page gets an injected UUID (uuid4 by default); duplicates and reuse
of any source page UUID are rejected. Source keys/target IDs remain exact strings.
No cover, title/dedication page, illustration, asset lookup or extra generated
page is introduced. N story pages equals N projected pages. Editing and front
matter require Agent 3's later model/counting decisions.

## Verification and integration boundary

Tests use synthetic accepted sources or offline fake execution only, with
pytest-socket denying network. Cover both languages, all age bands/boundaries and
open-ended ages, light/standard densities, 1/6/27/32 pages, configurable product
limit, Roy ordered targets, strict scalars/controls, construction bypasses,
correlation/owner mismatches, exact UTF-8 byte boundaries and conservative bounds.

Canonical capacity does not imply a live runtime can generate 32 pages. Existing
v1/v2 schemas, error codes and behavior stay unchanged. No shared DTO ambiguity
was resolved by adding product APIs; their final integration, source ownership
provenance, persistence and access controls remain Agent 3 dependencies.
