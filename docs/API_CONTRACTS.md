## Executable boundary after milestone 1

Existing v1/v2 routes are unchanged. `/v3/books`, `/v3/books/manual`, `/v3/books/ai`,
`/v3/jobs/stories` and private detail paths remain unmounted (404, tested).
`api/book_dtos.py` exports typed BookDetailResponse, ManualBookCreateRequest and title-update
contracts for future integration; these are not yet published OpenAPI routes. BookDetail includes
schema version, UUID, mode/state/revision, title/language/direction, UTC timestamps, flat origin,
ordered pages and asset bindings. Each PageDocument v1 contains layout and discriminated text/image
blocks. Text-only AI serialization omits absent frame fields to match Agent 1's projection exactly.
Future authenticated/anonymous adapters must scope repository access and translate only fixed safe
errors; never expose SQL exceptions or Pydantic input values. The service is internal, not an
anonymous-access implementation. Existing v2 output shapes and generation behavior are unchanged.


# Product API contracts - Phase A proposal

> **Current delivery, 2026-11-05:** Phase B milestone 1 is implemented internally only: canonical Book/PageDocument, SQLAlchemy storage, migration 0002 and transactional services. No v3 routes, ownership, catalog, worker or quota implementation is enabled. Later design sections remain proposals. The latest session design is **7-day idle plus 30-day absolute expiry**, superseding the earlier fixed-30-day-only proposal. See [current handoff](PERSISTENCE_HANDOFF.md) and [expanded backend roadmap](BACKEND_ROADMAP.md).
Status: **Phase A including anonymous/quota design accepted in principle; milestone 1 implemented; later coding unauthorized**. No new endpoints/OpenAPI components implemented. Existing generation API is documented in [API.md](API.md), and remains authoritative. This document proposes new shapes and DTO responsibilities for the later API workstream. See [ARCHITECTURE.md](ARCHITECTURE.md) and [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md).

Current delivery plan: [PHASE_B_IMPLEMENTATION_PLAN.md](PHASE_B_IMPLEMENTATION_PLAN.md).
User-proposed planning defaults now select UTC/10+10, committed dispatch consumption
and proven-pre-dispatch release, 7-day idle / 30-day absolute anonymous sessions (with idle
cutoff), >=48-hour terminal replay, quota-free guest previews and a separate async
POST `/v3/jobs/stories` returning 202 for new work. Agent 1 `49410d0` aligns on
separate routes/replay and cancelled operation state. No endpoint is implemented.

## Versioning, exposure and common rules

Add `/v3` for the Book product API; retain POST `/v1/stories/generate` (deprecated) and `/v2/stories/generate` domain payloads, ordinary generation success/failure shapes, cancellation and engine budgets. No mandatory saving or save query parameter is added to them. The new anonymous access/quota boundary must cover every publicly exposed AI route, including legacy routes, so v1/v2 cannot bypass v3 limits. Its new session/CSRF/429 transport behavior requires coordinated client rollout, not a claim of identical HTTP behavior; legacy engine mappings remain unchanged. This supersedes the earlier unapproved save=true integration proposal. Story schema "2", PageDocument schema "1" and HTTP v3 are distinct versions.

Public catalog routes serve only published, public, localized products with an eligible template release and cleared sample media. Unlisted products may be reached by slug but never listed; hidden/retired/missing localization return 404. Catalog/schema/sample browsing needs no account or session. Template preview/personalization and AI story/image creation also need no account: bootstrap an anonymous session and enforce session-scoped access. Persisted Books/results remain private to that principal or its future verified account claim, never a public anonymous library. No caller-supplied owner ID, UUID or Origin grants ownership. Catalog authorship/publication remains developer-provisioned. Current executable private APIs remain absent; a future anonymous rollout requires the proposed security/quota implementation and release review, not account registration.

All inputs use strict extra-forbidden typed schemas, finite bounded numerics/strings/arrays and configured body/page/block/preview limits. Generation languages remain en/he; new locale options are not additional generation-language support. Missing catalog locale returns 404; no silent translation/fallback. UUIDs are opaque public resource IDs, never storage object keys. Private and personalized responses use Cache-Control: no-store and server-generated X-Request-ID; no sensitive query parameters or logging. Custom error handlers must not expose Pydantic inputs, SQL, credential-bearing URLs or diagnostics.

Every successful Book read/mutation returns a strong ETag, `"book:<uuid>:<revision>"`. Every existing-Book mutation requires exactly one matching If-Match; missing -> 428 PRECONDITION_REQUIRED, stale -> 412 REVISION_CONFLICT. Revision is a positive JSON integer and increments once per atomic command, even for page-only edits. Wrong lifecycle -> 409 BOOK_NOT_EDITABLE; finalized/archived cannot be edited. Missing or inaccessible resources share 404. A retry is not an overwrite/merge; reload the new revision and ask the adult how to proceed. Client-generated IDs or PATCH bodies cannot change origin, source IDs, revision, owner or lifecycle directly.

## Endpoint inventory

| Method / path | Request / response | Semantics |
| --- | --- | --- |
| POST `/v3/session` | empty JSON / SessionContext | 201 for new anonymous session, 200 for existing valid one; secure HttpOnly cookie, CSRF token and expiry in no-store response; no signup/child details; origin/rate/bot protected |
| GET `/v3/session` | SessionContext | 200 session mode/expiry/CSRF context, 401 if absent/expired; no bearer token/owner ID in body |
| DELETE `/v3/session` | no body / 204 | revoke current credential, clear cookie; CSRF required; does not reset quota or imply data erasure |
| POST `/v3/session/claim` | empty JSON / SessionContext | future verified-account plus fresh anonymous possession/CSRF/login-bound proof; atomically transfer namespace and revoke guest credential; unavailable until real identity adapter exists |
| GET `/v3/usage` | DailyUsage | session-authorized separate story/image quota counters and UTC reset; informational snapshot, never guarantees admission |
| GET `/v3/products?language=he&category=learning&limit=20&cursor=...` | CatalogQuery / ProductList | 200, published/public only, optional strict nonnegative age_months discovery filter, bounded limit <= configured cap; opaque cursor bound to filters, order `(created_at DESC,id DESC)`; no personal data |
| GET `/v3/products/{slug}?language=he` | ProductDetail | 200, localized title/description/age guidance, creation mode TEMPLATE_BASED, current template/version, finite page variants and public gallery |
| GET `/v3/products/{slug}/previews?language=he` | ProductPreviewList | 200, ordered public synthetic sample asset references with localized alt text; never customer preview URLs |
| GET `/v3/template-versions/{version_id}/personalization-schema?ui_language=he` | PersonalizationSchemaResponse | 200, eligible published version, content language, schema/renderer versions, fields/defaults/options, localized labels; no authored manuscript AST |
| POST `/v3/template-previews` | TemplateChoices / PersonalizedPreview | 200, anonymous/account session + CSRF, no signup; schema-validated ephemeral in-memory response; no Book, saved choices, LLM/image call or AI quota consumption; separate preview abuse limits |
| POST `/v3/books/from-template` | TemplateChoices / BookDetail | 201 + Location + ETag, atomically saves choices/pinned source/rendered pages/assets; exactly the version explicitly selected |
| POST `/v3/books/ai` | unchanged StoryRequestV2 body / AIBookCreated | 201 + Location + ETag, generates via existing engine and saves accepted source+Book atomically; explicit page_count mandatory; no provider/model selection from client |
| POST `/v3/images/generate` | ImageCreationRequest / ImageCreated | anonymous/account session + CSRF + Idempotency-Key; one generated image per operation; consumes image quota only, accepted output becomes a scoped private Asset; image implementation/safety contract pending Agent 1 |
| POST `/v3/jobs/stories` | StoryRequestV2 / OperationAccepted | proposed separate async 202 + Location operations/{id} + polling Retry-After; same story quota/key scope as synchronous creation; exact execution contract needs joint Agent 1 approval |
| GET `/v3/operations/{operation_id}` | OperationStatus | owner-scoped status/result references, never raw prompt/partial content; supports idempotent reconnect; execution-state enum and async semantics must be finalized with Agent 1 |
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

All Book/image/operation/generation routes require an anonymous or account access context, not registration. Mutations also require CSRF. Catalog routes never inspect private tables. No upload, signed-upload token, provider diagnostic, template publishing/admin, registration or commerce endpoints are included. Existing ready assets may be assigned by asset_id; service verifies access/readiness. Asset delivery uses an approved resolver; never accept a caller URL or expose object_key. Private delivery references, if returned, are short-lived and no-store, not persisted; signed references are scoped bearer grants and must not leak into telemetry or public previews.

## Anonymous access, quotas and frontend contract delta

Session bootstrap returns `{"mode":"anonymous","expires_at":"2026-12-05T10:00:00Z","csrf_token":"<opaque session-bound value>"}` for issuance on 2026-11-05T10:00:00Z (30 fixed days); that token string is a schema placeholder, not a stored credential. Cookie is the opaque Secure/HttpOnly/SameSite=Lax host-only token described in ARCHITECTURE.md. Send CSRF as `X-CSRF-Token`, never a URL parameter. Bootstrap reuses a valid session; rotation does not allocate a new owner/allowance or extend expiry; no seven-day idle expiration applies. Session expiry returns 401 SESSION_REQUIRED; frontend explains lost/expired anonymous access instead of silently retrying a paid request under a fresh principal. A new anonymous session never gains access to old resources just because the browser retained their IDs. Logout/revocation does not reset counters. No registration screen is required for normal creation.

DailyUsage example (UTC fields are authoritative; frontend may display local reset time):

```json
{
  "policy_version": "daily-ai-attempts-v1",
  "timezone": "UTC",
  "day": "2026-11-05",
  "reset_at": "2026-11-06T00:00:00Z",
  "capabilities": {
    "story_generation": {"limit": 10, "consumed": 3, "reserved": 1, "remaining": 6},
    "image_generation": {"limit": 10, "consumed": 2, "reserved": 0, "remaining": 8}
  }
}
```

Remaining is max(0,10-consumed-reserved) for the authorized canonical namespace set. Claim may make totals exceed 10; report actual totals and zero remaining, not reset/clamp history. Daily slots reserve at admission; dispatched failures/refusals/unsafe output/timeouts still count, retries within one engine operation do not double-count. Proven pre-dispatch validation/cancelled work does not consume a slot; provisional reservation may be released only with a dispatch fence. This is a creation-attempt allowance, not ten guaranteed successes. Manual/template/preview/editorial-image usage is free of AI units but separately abuse-limited. No extra hidden images in story generation; each newly generated image has its own image admission.

V3 AI POSTs require Idempotency-Key (random >=128-bit client value, bounded ASCII; retained for the operation's pending lifetime plus proposed >=48h terminal replay window). Same authorized key/capability/fingerprint returns the same operation/result without new quota or provider work; a changed payload or conflicting claimed-namespace key returns 409 IDEMPOTENCY_CONFLICT. Store only keyed digests/fingerprints, not the raw key/request. Frontend keeps one key for a deliberate creation and uses it on transport recovery, never a new key as an automatic retry. Repeated retrieval/reconnect is free; regeneration explicitly uses a new key/unit. No claim of exactly-once upstream delivery.

Proposed key syntax is 22-128 base64url characters; frontend uses a CSPRNG (recommend 256 random bits). Syntax checks cannot prove entropy, so do not treat a caller key as an access credential. Expired keys may no longer deduplicate and must not be reused for automatic recovery. Account claim preserves authorized replay scope across original namespaces; it does not revive revoked guest credentials.

ImageCreationRequest v1 is proposed as `{schema_version:"1",prompt:string,language:"en"|"he",aspect_ratio:"square"|"portrait"|"landscape"}` with server-bounded prompt length and exactly one output; no credentials/provider/model/owner/batch fields. Do not embed a child profile by default. ImageCreated returns `{operation_id,image_generation_id,asset:{asset_id,media_type,width,height}}` plus an authorized delivery reference if available; no raw provider URL/diagnostics. Assign to a page in a separate authorized If-Match command, not by arbitrary target ID in the generation request. Safety/input/media-size policies and provider capability support must be agreed with Agent 1 before executable DTOs or an endpoint exist.

New daily exhaustion returns 429 DAILY_LIMIT_REACHED, capability + reset_at + remaining=0, and Retry-After seconds until the next UTC boundary. ABUSE_THROTTLED is a distinct 429 with its own retry delay; a bot challenge uses 403 CHALLENGE_REQUIRED and an opaque action descriptor, not prompts/child data passed to a challenge vendor. 503 ADMISSION_UNAVAILABLE means quota storage unavailable/uncertain, no speculative dispatch. Missing session=401 SESSION_REQUIRED; bad/missing CSRF=403 CSRF_REJECTED. Do not automatically retry any provider-creating POST after these responses. Daily counter reads are advisory: another tab may claim the last slot before POST. Even remaining>0 can be denied by independent safety/spend/abuse limits.

Legacy v1/v2 compatibility proposal: the same session/CSRF/admission gate applies before their unchanged engine routes in any public deployment. Preserve existing GenerationFailure JSON fields and enum values for gate failures: 401 INPUT_INVALID (session required), 403 POLICY_REJECTED (CSRF/access rejected), 429 BUDGET_EXCEEDED (daily/abuse gate); stage=validation, safe fixed messages, empty usage, no draft. Convey distinct daily/abuse reason and quota/reset in documented response headers, not new legacy domain error codes. V3 uses the explicit new codes above. This adds documented transport statuses/headers and session bootstrap to legacy callers; Agent 2/4 must validate compatibility rather than claiming zero behavioral change. Legacy optional Idempotency-Key can deduplicate; without it each POST is a new operation/unit. Do not leave v1/v2 as publicly exposed quota-free alternatives. Existing local/fake tests and route code are unchanged now.

Gate header names: `X-StoryForge-Limit-Reason: daily|abuse`, `X-StoryForge-Capability: story_generation|image_generation`, `X-StoryForge-Limit`, `X-StoryForge-Remaining`, `X-StoryForge-Reset-At` (ISO UTC, daily only), and standard Retry-After (seconds). Return only the caller's relevant quota information; never expose raw network-risk signals or other principals' IDs. No image unit is silently deducted for a legacy story route.

Agent 2 changes required later: use same-origin credentials (current optional v2 adapter uses `credentials: omit`), bootstrap session with no registration wall, keep CSRF only in memory, send CSRF/Idempotency-Key/If-Match where required, show separate ten-unit counters and attempt-count/failure/reset rules, render ephemeral template previews without auto-saving, and list/reopen only session-owned saved Books. Cache/session/account changes must clear private in-memory results; do not use localStorage for bearer tokens or child drafts. Future account claim UI is opt-in and must explain shared-device access and inheritance of usage. CORS/proxy and cookie settings must be reconciled before actual browser-to-backend testing.

## Agent 1 reliability / asynchronous-generation dependency

Agent 1's latest read-only inspected integration contract is `49410d0`, following reliability `19d63f7` and earlier integration `e34b588`. It reconciles committed Agent 3 `7e38326`, recognizes anonymous ownership/accepted persistence, and now aligns separate async and sync paths. The Phase B plan additionally applies the user's newer 7-day idle / 30-day absolute session default, replacing its seven-day-idle candidate. Other queue/lease/snapshot/finalization-recovery defaults remain approval dependencies. These are aligned planning contracts, not authorization or runtime evidence:

- One durable operation ID, reservation and idempotency record shared by HTTP admission, story/image execution and status polling. Do not create competing admission/job ledgers. Durable dispatch/outbox acceptance must be atomic with reservation/source creation; no quota count at each worker delivery.
- Separate `POST /v3/jobs/stories` -> 202 + Location `/v3/operations/{id}` + polling Retry-After is the primary frontend target; replay of an existing matching key -> 200 current OperationStatus + same Location, no enqueue. Job ID is the operation ID, not another ledger. Public states are queued/processing/completed/failed/cancelled; source cancellation stays failed/CANCELLED. Plan POST `/v3/operations/{id}/cancel` with an atomic cancel/completion winner; exact request/response/error DTOs are milestone-5 contract gates. Polling disconnect does not cancel async work. Existing v1/v2 stay synchronous; no 202 is silently substituted there.
- If implementing sync `/v3/books/ai`, new work returns 201 on atomic completion; matching completed key returns 200 same accessible Book/source; queued/processing key returns 409 OPERATION_IN_PROGRESS + operation Location, never attaches a second runner; terminal failed/cancelled replays the safe outcome. Key/capability/request fingerprint excludes route/transport, so switching routes cannot change the first-admitted execution/disconnect policy or start a new run. A future async image route needs separate provider/safety approval.
- Lease/fencing and first-dispatch authorization must prevent duplicate worker sends or late dispatch after release. Unknown-send recovery must not rerun an entire story engine with a fresh three-attempt budget. Preserve attempts/deadlines/cost reservations and safe accounting across any allowed resume; one creation reservation is not permission for unbounded retries.
- Authorize the first quota dispatch at the actual first attempt journal boundary, not merely engine/worker startup. Coordinate its transaction/fence with Agent 1's before-I/O attempt/token/cost journal; pre-provider validation failures must remain releasable. No provider adapter becomes the quota authority. A future chunked job still uses one story unit, but its proposed seven-call pilot is not authorized and cannot bypass the existing three-call setting.
- Disconnect versus job cancellation: synchronous disconnect currently cancels request-local work; durable async work may survive browser disconnect and remain reserved/consumed. That semantic change needs explicit agreement. No implicit async job, worker or cancellation-route implementation is authorized here.
- Session expiry/claim/revocation never cancels ownership scoping: jobs carry immutable issuance owner IDs and resolve current claim scope before result delivery, not a serialized browser cookie. Agent 1 must define encrypted short-lived request-envelope storage if async execution requires sensitive inputs after HTTP returns; current minimized source metadata is not enough to replay input. Child prompts may not be added casually to logs/operation JSON.
- Agent 1's private resume snapshot may contain validated plan/chunk content under separately approved encryption, access and retention. Never store failed/unsafe drafts or those partials in completed source/Book pages. Freeze execution configuration/fingerprints at admission, queue expiry separately from execution deadline, and preserve remaining deadlines across hosts without persisting monotonic-clock values. Replaying an existing key after policy deployment uses its stored admitted fingerprint/snapshot, not a new-policy rerun.
- Image-safety disposition, provider timeouts, duplicate callbacks, completion/source+Book atomicity, cleanup and terminal quota settlement need joint story/image tests. No claim of runtime reliability/async/image coverage now.

Latest-contract details to implement/test in milestone 5: persist canonicalizer/input-schema/digest-key versions and retain compatible verification keys throughout live/replay retention; locate existing authorized key before new-job validation/capacity. Missing verifier fails closed, unsupported historical interpretation returns 409 IDEMPOTENCY_VERSION_UNSUPPORTED with authorized operation reference, not new work. Erased result returns 410 RESULT_DELETED via a minimal authorized tombstone; never recreate a deleted Book from source on replay. Freeze all execution/profile/prompt/schema/pricing/rubric/capacity policies at admission and preflight canonical PageDocument worst-case bytes before quota/provider work. Journal daily consumption plus attempt/token/cost authorization in one transaction before first send. Unknown sends do not auto-replay; accepted-result storage-only recovery requires separately approved encrypted envelope/expiry settings. Restricted diagnostics/stop_reason persistence remains a separate allowlist review, not public polling content. Image provider scope is not automatically authorized by this story-engine contract.

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

Codes: 422 INPUT_INVALID / PERSONALIZATION_INVALID / DOCUMENT_INVALID (safe issue field IDs, never supplied values); 404 NOT_FOUND; 409 BOOK_NOT_EDITABLE / TEMPLATE_UNAVAILABLE / ASSET_UNAVAILABLE / IDEMPOTENCY_CONFLICT; 412 REVISION_CONFLICT; 428 PRECONDITION_REQUIRED (If-Match or required Idempotency-Key missing); 413 REQUEST_TOO_LARGE; 503 PERSISTENCE_UNAVAILABLE / ADMISSION_UNAVAILABLE. Session, CSRF, challenge and 429 codes are specified above. No hidden 2xx partial save. Unexpected failures use a fixed INTERNAL_ERROR and safe request ID. Account-only claim eventually requires a verified account, but ordinary creation/preview never returns an account-registration requirement.

V3 AI engine failures preserve existing code/status mappings and safe quality/usage, with a nullable generation_id/operation_id and no book/content. Domain generation errors are not recast as document-edit errors. For the synchronous contract the existing request disconnect watcher remains the execution boundary; extend its approved cleanup only to record terminal failure/settlement using a bounded awaited transaction. After dispatch a failed/cancelled operation still consumes its unit. A process crash may leave processing/unknown; no background recovery promise. Any durable async change awaits the Agent 1 agreement above.

If admission/source/create/start fails, return 503 before any AI call and release only a proven un-dispatched reservation safely. If post-generation commit fails or outcome is unknown, return 503 PERSISTENCE_UNAVAILABLE with known generation_id/operation_id, `retryable:false`, and explicit generation-outcome metadata `generation_attempted:true`, `save_outcome:"unknown"` (or `"not_saved"` only when rollback is established). Consumed usage is not rolled back with failed persistence. Do not return accepted content as a saved Book. Client may GET that operation/generation to resolve a completed link; processing is not proof of a failed provider call. V3 idempotency now is a required design dependency for admission/replay, not implemented functionality or a license for speculative redispatch. A repeated key can look up the existing operation, never automatically start a new provider run. Manual/template POST idempotency remains a separate decision; absent that, retries may duplicate resources and clients must not claim exactly-once behavior.

## OpenAPI and verification contract

Phase C will declare named DTOs/discriminators/examples, all success/error statuses, cookie session/CSRF security schemes, Idempotency-Key/ETag/If-Match/Location/Retry-After/quota headers, cursor constraints and `Cache-Control` in FastAPI OpenAPI. Mark catalog public, creation/preview anonymous-or-account session-scoped and claim account-only; no blanket registration requirement. Check `/openapi.json` snapshots and validate examples through the same Pydantic JSON boundary models. Phase A Markdown is a reviewed design, **not generated/validated OpenAPI evidence**. Agent 2 should not generate a client from nonexistent v3 routes yet.

Phase D required scenarios: unit tests for every scalar/placeholder branch and literal injection; dynamic required/default/localization rules; non-executable inputs; template publication/version sealing and release races; fixed/configurable page variants; manual empty/create/add/remove/reorder/replace/reopen/finalize/archive; stale/missing revision; cross-book page/asset attacks; multilingual logical order; unsafe asset/URL/control rejection; accepted AI-to-Book projection, failed draft exclusion, existing v1/v2 compatibility and exact invocation/budget counts. Real PostgreSQL tests must cover shared source+Book atomic rollback, deferrable reordering, unique/FK/check/immutability constraints, publication races, read/write consistency, optimistic edit winners, upgrade/downgrade and optional backfill rerun. ASGI tests use fake providers only. Browser-to-backend testing requires separately approved branch integration and Agent 2/4 execution; no such E2E run is claimed. Run complete combined regression tests and builds after code implementation; preserve separate SQLite/mock versus PostgreSQL result counts.

Additional revision tests required: anonymous bootstrap/rotation/revocation/fixation/CSRF and cookie flags; two anonymous sessions cannot read/edit/deliver each other's Books/images/operations; session loss cannot claim by UUID; preview leaves no Book/personalization/provider/quota rows and never becomes public. Real PostgreSQL race tests must admit exactly ten of many simultaneous requests per capability, permit independent story/image buckets, replay one key only once, reject conflicting fingerprints, and cover rollback/uncertain commit, dispatch fences, duplicate settlements and post-dispatch failures. Test UTC midnight while locks are held, operation replay/completion on the next day, multi-process admission and DB fail-closed behavior. Claim tests cover pending work, two competing accounts, inherited usage >10, old-cookie revocation, alias replay and no extra allowance after rotation/login/logout; legacy ownerless rows remain inaccessible. Mock network-risk/challenge signals without child data and exercise proxy/NAT rules. Any async durability/crash/recovery tests require Agent 1's settled design; actual browser cookie/proxy flows require Agent 2/4 execution. None has run for this documentation-only revision.
