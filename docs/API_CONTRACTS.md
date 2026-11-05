# Product API contracts - Phase A proposal

Status: **awaiting approval; no new endpoints/OpenAPI components implemented**. Existing generation API is documented in [API.md](API.md), and remains authoritative. This document proposes exact new endpoint shapes and named DTO responsibilities for Phase C. See [ARCHITECTURE.md](ARCHITECTURE.md) and [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md).

## Versioning, exposure and common rules

Add `/v3` for the Book product API; retain POST `/v1/stories/generate` (deprecated) and `/v2/stories/generate`, including their request validation, success/failure shapes, status mappings, cancellation and budgets. No mandatory saving or save query parameter is added to those endpoints. This supersedes the earlier **unapproved** save=true integration proposal in the handoff. Story schema "2", PageDocument schema "1" and HTTP v3 are distinct versions.

Public catalog routes serve only published, public, localized products with an eligible template release and cleared sample media. Unlisted products may be reached by slug but never listed; hidden/retired/missing localization return 404. Private Book/generation and personalized-preview routes are **not mounted by default** until authentication exists. An explicit synthetic-local configuration can mount them on a loopback-bound development server, with no public proxy. This is not an authorization implementation; never interpret a client owner ID, UUID or Origin header as ownership. Catalog authorship/publication remains developer-provisioned; no unauthenticated admin API.

All inputs use strict extra-forbidden typed schemas, finite bounded numerics/strings/arrays and configured body/page/block/preview limits. Generation languages remain en/he; new locale options are not additional generation-language support. Missing catalog locale returns 404; no silent translation/fallback. UUIDs are opaque public resource IDs, never storage object keys. Private and personalized responses use Cache-Control: no-store and server-generated X-Request-ID; no sensitive query parameters or logging. Custom error handlers must not expose Pydantic inputs, SQL, credential-bearing URLs or diagnostics.

Every successful Book read/mutation returns a strong ETag, `"book:<uuid>:<revision>"`. Every existing-Book mutation requires exactly one matching If-Match; missing -> 428 PRECONDITION_REQUIRED, stale -> 412 REVISION_CONFLICT. Revision is a positive JSON integer and increments once per atomic command, even for page-only edits. Wrong lifecycle -> 409 BOOK_NOT_EDITABLE; finalized/archived cannot be edited. Missing or inaccessible resources share 404. A retry is not an overwrite/merge; reload the new revision and ask the adult how to proceed. Client-generated IDs or PATCH bodies cannot change origin, source IDs, revision, owner or lifecycle directly.

## Endpoint inventory

| Method / path | Request / response | Semantics |
| --- | --- | --- |
| GET `/v3/products?language=he&category=learning&limit=20&cursor=...` | CatalogQuery / ProductList | 200, published/public only, optional strict nonnegative age_months discovery filter, bounded limit <= configured cap; opaque cursor bound to filters, order `(created_at DESC,id DESC)`; no personal data |
| GET `/v3/products/{slug}?language=he` | ProductDetail | 200, localized title/description/age guidance, creation mode TEMPLATE_BASED, current template/version, finite page variants and public gallery |
| GET `/v3/products/{slug}/previews?language=he` | ProductPreviewList | 200, ordered public synthetic sample asset references with localized alt text; never customer preview URLs |
| GET `/v3/template-versions/{version_id}/personalization-schema?ui_language=he` | PersonalizationSchemaResponse | 200, eligible published version, content language, schema/renderer versions, fields/defaults/options, localized labels; no authored manuscript AST |
| POST `/v3/template-previews` | TemplateChoices / PersonalizedPreview | 200, private local gate; validates schema/options and renders ordered PageDocument preview in memory; no Book created, no LLM/image generation, no persistent preview token |
| POST `/v3/books/from-template` | TemplateChoices / BookDetail | 201 + Location + ETag, atomically saves choices/pinned source/rendered pages/assets; exactly the version explicitly selected |
| POST `/v3/books/ai` | unchanged StoryRequestV2 body / AIBookCreated | 201 + Location + ETag, generates via existing engine and saves accepted source+Book atomically; explicit page_count mandatory; no provider/model selection from client |
| GET `/v3/generations/{generation_id}` | GenerationStatus | 200 private, existing story lifecycle and fixed error code, nullable completed book_id; no draft/plan/child request metadata or raw attempts; resolves a known ID after an ambiguous storage response |
| POST `/v3/books/manual` | ManualBookCreate / BookDetail | 201 + Location + ETag, draft metadata and optional initial typed pages; empty draft allowed |
| GET `/v3/books?limit=20&cursor=...&state=draft` | BookList | 200 private, keyset pagination `(created_at DESC,id DESC)`; summary only, no personalization/child profile/page text; eventual owner-scoped query, never public all-user library |
| GET `/v3/books/{book_id}` | BookDetail | 200 + ETag; current metadata/origin/revision and ordered pages; policy caps bound response size |
| GET `/v3/books/{book_id}/pages` | BookPages | 200 + ETag; all ordered pages from one revision (initial bounded page counts), no independent mixed-revision pagination |
| PATCH `/v3/books/{book_id}` | BookMetadataPatch / BookDetail | 200 + ETag, only supplied title field initially; language changes require a new book, no silent translation |
| POST `/v3/books/{book_id}/pages` | PageAdd / BookDetail | 200 + ETag, insert at one-based position 1..N+1, stable server page UUID; later positions shift atomically |
| PUT `/v3/books/{book_id}/pages/{page_id}` | PageReplace / BookDetail | 200 + ETag, replace entire bounded PageDocument and authorized asset bindings; position unchanged |
| DELETE `/v3/books/{book_id}/pages/{page_id}` | no body / BookDetail | 200 + ETag, remove and compact order; may leave draft empty |
| PUT `/v3/books/{book_id}/page-order` | PageOrder / BookDetail | 200 + ETag, exact permutation of current page IDs; no drops, duplicates or invented pages |
| POST `/v3/books/{book_id}/finalize` | no body / BookDetail | 200 + ETag, validate final document and asset/policy requirements, draft -> finalized; no LLM call |
| POST `/v3/books/{book_id}/archive` | no body / BookDetail | 200 + ETag, draft/finalized -> archived; not erasure or public publishing |

All Book routes, generation status and personalized previews require the private gate/access context. Their catalog counterparts never inspect private tables. No upload, signed-upload token, provider diagnostic, template publishing/admin, export, account or commerce endpoints are included. Existing ready assets may be assigned by asset_id; assignment/read service verifies access and media readiness. Asset delivery uses the injected approved resolver; never trust a supplied URL or expose object_key. Private delivery references, if returned, are short-lived and no-store, not persisted.

## Named DTO examples

Examples are original synthetic fixtures, not competitor content, generated manuscripts or executed API requests. UUIDs below are illustrative. Required fields shown in examples are normative for the proposed DTO; optional fields/defaults are described alongside. Unknown properties are forbidden. Server limits apply even when an authored schema requests larger values.

### Product detail and personalization schema

```json
{
  "product_id": "10000000-0000-4000-8000-000000000001",
  "slug": "letters-in-the-garden",
  "language": "he",
  "supported_languages": ["he", "en"],
  "title": "אותיות בגינה",
  "description": "ספר אותיות אישי לדוגמה",
  "category": "learning",
  "creation_mode": "TEMPLATE_BASED",
  "recommended_age_months": {"minimum": 0, "maximum": 72},
  "template_version_id": "20000000-0000-4000-8000-000000000001",
  "page_variants": [{"variant_id": "standard", "label": "מלא", "page_count": 27}],
  "cover": {"asset_id": "30000000-0000-4000-8000-000000000001", "alt": "כריכת ספר לדוגמה"}
}
```

```json
{
  "template_version_id": "20000000-0000-4000-8000-000000000001",
  "content_language": "he",
  "ui_language": "en",
  "schema_version": "1",
  "renderer_version": "template-renderer-v1",
  "fields": [
    {"id": "child_name", "type": "text", "required": true, "min_length": 1, "max_length": 40, "label": "Child's name", "help": null},
    {"id": "character", "type": "choice", "required": false, "default": "character_a", "label": "Character", "options": [{"id": "character_a", "label": "Character A"}, {"id": "character_b", "label": "Character B"}]},
    {"id": "cover_color", "type": "choice", "required": false, "default": "green", "label": "Cover color", "options": [{"id": "green", "label": "Green"}, {"id": "blue", "label": "Blue"}]},
    {"id": "dedication", "type": "text", "required": false, "default": "", "min_length": 0, "max_length": 500, "label": "Dedication", "help": null}
  ]
}
```

Authored PersonalizationSchema v1 contains those same field rules plus a localized label/help map per field/option; the public response resolves ui_language. Choice values are stable option IDs, not labels/color CSS or asset paths. Boolean fields use required/default and labels; integer fields add strict minimum/maximum. Empty optional dedication is permitted only by its declared rule. No arbitrary regular expressions or executable custom validators. Template choices are a bounded map of JSON scalar union string/bool/int; application validates the exact field/type set against the pinned schema. OpenAPI describes the scalar union and personalization-schema DTO; it cannot statically enumerate runtime product-specific keys. Dynamic validation failures return safe field IDs/fixed issue codes without input values.

### Template preview or instantiate

```json
{
  "template_version_id": "20000000-0000-4000-8000-000000000001",
  "page_variant_id": "standard",
  "values": {"child_name": "אור", "character": "character_a", "cover_color": "green", "dedication": "באהבה"}
}
```

POST template-previews returns `{"schema_version":"1","template_version_id":"...","page_variant_id":"standard","page_count":27,"pages":[...]}`; pages use `{page_key,position,document}` with every page present in deterministic order. Preview IDs/page keys are not editable Book UUIDs. Instantiate returns the BookDetail shape below with creation_mode TEMPLATE_BASED, source version/product/variant display snapshot and stored fully resolved choices accessible only in the private detail DTO. A retired/blocked/not-eligible version returns 409 TEMPLATE_UNAVAILABLE; never replace it with a new release without adult confirmation.

Internal authored text example: `{"segments":[{"kind":"literal","value":"שלום "},{"kind":"field","field_id":"child_name"}]}`. `select` uses a declared choice field and finite option-to-segment lists, with bounded depth. Referenced fields must exist, all branches must validate before publication, and every media choice resolves a pinned template_version_assets slot. A value such as `{{secret}}` is literal output, never evaluated; unsafe controls/content are rejected by policy. No template source AST is returned to catalog clients.

### Manual draft and page editing

```json
{
  "schema_version": "1",
  "title": "לילה בגינה",
  "language": "he",
  "pages": [
    {"document": {"schema_version": "1", "layout": {"preset": "text-only-v1"}, "blocks": [
      {"kind": "text", "block_id": "opening", "language": "he", "direction": "rtl", "style": "body", "sentence_units": ["אור רואה כוכב."]}
    ]}, "asset_bindings": []}
  ]
}
```

ManualBookCreate requires schema_version/title/language; pages defaults to []. Every initial page uses the same `{document,asset_bindings}` wrapper, including text-only pages. Block IDs are stable bounded ASCII keys unique per page (not row UUIDs), style/preset are registry enums, text/sentence units have bounded counts/length. Image block: `{"kind":"image","block_id":"picture","slot_key":"hero","fit":"contain"}` with PageAdd/PageReplace `asset_bindings:[{"slot_key":"hero","asset_id":"30000000-0000-4000-8000-000000000001"}]`. Every image slot has exactly one authorized binding; no orphan bindings. Layout preset validates allowed block kinds and any bounded position/crop fields; arbitrary CSS/layout extensions fail.

PageDocument v1 initially allows `text-only-v1` and `text-image-v1` presets, `body`/`title`/`caption` text styles, and image fit `contain`/`cover`. An optional frame or crop is exactly `{x,y,width,height}` with finite normalized numbers: x/y >=0, width/height >0, x+width <=1 and y+height <=1. Layout-specific required fields are discriminator-validated. No absolute device pixels, extra rendering commands, custom fonts or arbitrary asset MIME types; initial ready images are PNG/JPEG/WebP, excluding executable SVG/HTML. Text block language/direction follows the reviewed en/he registry, independently of interface locale. Policy caps on payload/text/block counts are server configuration to approve before Phase B, not values a template author can override.

Canonical ManualBookCreate wire shape (used by OpenAPI/tests):

```json
{"schema_version":"1","title":"My Garden","language":"en","pages":[{"document":{"schema_version":"1","layout":{"preset":"text-only-v1"},"blocks":[{"kind":"text","block_id":"opening","language":"en","direction":"ltr","style":"body","sentence_units":["Or watches a star."]}]} ,"asset_bindings":[]}]}
```

PUT page body is `{"document":PageDocument,"asset_bindings":[]}`; POST page adds `"position":2`. PUT page-order body is `{"page_ids":["<existing-page-uuid-2>","<existing-page-uuid-1>"]}`. PATCH Book is `{"title":"A new title"}`. Finalize/archive have no body. All require If-Match as above. Manual page count is edited structurally, never via a page_count metadata patch. Limits are configurable independently from AI admission; Phase B must set/review them, with no hidden age-length rule.

### Common Book response and AI adaptation

```json
{
  "schema_version": "1",
  "book_id": "40000000-0000-4000-8000-000000000001",
  "creation_mode": "MANUAL",
  "state": "draft",
  "revision": 1,
  "title": "My Garden",
  "language": "en",
  "direction": "ltr",
  "page_count": 1,
  "created_at": "2026-11-05T10:00:00Z",
  "updated_at": "2026-11-05T10:00:00Z",
  "origin": {"generation_id": null, "template_version_id": null, "page_variant_id": null, "source_display": null},
  "personalization": null,
  "pages": [{"page_id":"50000000-0000-4000-8000-000000000001","position":1,"document":{"schema_version":"1","layout":{"preset":"text-only-v1"},"blocks":[{"kind":"text","block_id":"opening","language":"en","direction":"ltr","style":"body","sentence_units":["Or watches a star."]}]},"asset_bindings":[]}]
}
```

BookDetail includes those fields; finalized_at/archived_at are optional nullable timestamps. Its origin union is discriminated by creation_mode: AI requires generation_id; template requires template_version_id/page_variant_id/source_display and personalization; manual has null sources/personalization. Server supplies all origin fields. BookPage response may additionally expose source_page_key/source_target_id for AI/educational provenance; these are immutable and never confused with new page UUIDs. BookList returns `{items:[BookSummary],next_cursor:null|string}`. BookSummary contains book_id/title/language/direction/creation_mode/state/revision/page_count/created_at only. BookPages returns `{book_id,revision,pages:[...]}`. GenerationStatus returns `{generation_id,status,book_id:null|string,error_code:null|string}`; completed Book linkage is durable, not inferred from a cached response.

AI request example uses the existing unchanged domain schema:

```json
{"schema_version":"2","display_name":"Or","age_months":0,"language":"en","theme":"Night garden","page_count":2,"story_type":"bedtime","text_density":"standard"}
```

AIBookCreated is `{book:BookDetail,generation:{generation_id,request_id,status:"completed",quality:QualityReport,usage:SafeUsageSummary,total_latency_seconds}}`. SafeUsageSummary uses the existing persistence allowlist and excludes new diagnostic fields until separately approved; internal raw errors never qualify. No second duplicated StoryV2 page array in v3. AI source sentence_units map losslessly into a single text block per BookPage, preserving language/direction and target/page source IDs. Source quality metadata describes the generated source, not later edited pages. The frontend's existing v2 StoryReader contract remains unchanged; Agent 2 adds a separate BookDocument reader/editor adapter.

## Errors, cancellation and storage ambiguity

V3 product errors use a named envelope, separate from unchanged v1/v2 error unions:

```json
{"status":"failure","request_id":"60000000-0000-4000-8000-000000000001","error":{"code":"REVISION_CONFLICT","message":"Reload this book before saving","retryable":false},"resource":{"book_id":"40000000-0000-4000-8000-000000000001","generation_id":null}}
```

Codes: 422 INPUT_INVALID / PERSONALIZATION_INVALID / DOCUMENT_INVALID (safe issue field IDs, never supplied values); 404 NOT_FOUND; 409 BOOK_NOT_EDITABLE / TEMPLATE_UNAVAILABLE / ASSET_UNAVAILABLE; 412 REVISION_CONFLICT; 428 PRECONDITION_REQUIRED; 413 REQUEST_TOO_LARGE; 503 PERSISTENCE_UNAVAILABLE. No hidden 2xx partial save. Unexpected failures use a fixed INTERNAL_ERROR and safe request ID. Future 401 AUTHENTICATION_REQUIRED is reserved for the real auth adapter, not fake identity emulation.

V3 AI engine failures preserve existing code/status mappings and safe quality/usage, with a nullable generation_id and no book/content. Domain generation errors are not recast as document-edit errors. The existing request disconnect watcher remains the execution boundary; extend its approved cleanup only to record terminal failure using a bounded awaited transaction. No detached tasks, checkpoints or provider retries are added. A process crash may leave processing; no background recovery promise.

If source/create/start fails, return 503 before any AI call. If post-generation commit fails or outcome is unknown, return 503 PERSISTENCE_UNAVAILABLE with known generation_id, `retryable:false`, and explicit generation-outcome metadata `generation_attempted:true`, `save_outcome:"unknown"` (or `"not_saved"` only when rollback is established). Do not return accepted content as a saved Book. Client may GET that generation ID to resolve a completed link; an unresolved processing row is not proof of a failed provider call. Do not automatically repeat POST. Durable idempotency for generation is not implemented/proposed as a shortcut; it must be designed before reliable automatic retries/production operation, including conflict fingerprints without retaining raw child input. Manual/template POST retries can likewise duplicate resources; clients must not claim exactly-once behavior.

## OpenAPI and verification contract

Phase C will declare named DTOs/discriminators/examples, all success/error statuses, ETag/If-Match/Location headers, cursor constraints, explicit local-only exposure and `Cache-Control` in FastAPI OpenAPI. Check `/openapi.json` snapshots and validate examples through the same Pydantic JSON boundary models. Phase A Markdown is a reviewed design, **not generated/validated OpenAPI evidence**. Agent 2 should not generate a client from nonexistent v3 routes yet.

Phase D required scenarios: unit tests for every scalar/placeholder branch and literal injection; dynamic required/default/localization rules; non-executable inputs; template publication/version sealing and release races; fixed/configurable page variants; manual empty/create/add/remove/reorder/replace/reopen/finalize/archive; stale/missing revision; cross-book page/asset attacks; multilingual logical order; unsafe asset/URL/control rejection; accepted AI-to-Book projection, failed draft exclusion, existing v1/v2 compatibility and exact invocation/budget counts. Real PostgreSQL tests must cover shared source+Book atomic rollback, deferrable reordering, unique/FK/check/immutability constraints, publication races, read/write consistency, optimistic edit winners, upgrade/downgrade and optional backfill rerun. ASGI tests use fake providers only. Browser-to-backend testing requires separately approved branch integration and Agent 2/4 execution; no such E2E run is claimed. Run complete combined regression tests and builds after code implementation; preserve separate SQLite/mock versus PostgreSQL result counts.
