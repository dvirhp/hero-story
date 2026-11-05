# Backend delivery extension (design only beyond milestone 1)

2026-11-05. Only Phase B milestone 1 is authorized and implemented. This extends
PHASE_B_IMPLEMENTATION_PLAN.md without authorizing accounts, commerce, jobs or payments.
Migration numbers after 0002 are tentative and must be assigned on the approved integration base.
All new private operations require effective principal authorization; UUID knowledge is never access.
Agent 1 owns engine/projection/reliability contracts, Agent 2 frontend integration, Agent 3 persistence,
and Agent 4 independent QA. No merging of their branches has occurred.

## Milestones 1-7: approved scope and future dependencies

| Milestone | Modules and migrations | Endpoints / DTOs | Dependencies and transaction rules | Tests / acceptance |
| --- | --- | --- | --- | --- |
| 1 Canonical persistence (implemented) | domain documents/books/capacity; application ports/service; persistence repository/UOW; 0002 Book/pages/assets/bindings | Internal ManualBookCreate, BookDetail, title-update only; no HTTP routes | Agent 1 supplies pure accepted projection; source completion + all canonical rows one transaction; ordered locked reads and expected-revision title CAS | Real PG rollback, constraints, 27-page Hebrew, races, migrations; all 835 regression tests pass |
| 2 Anonymous security / ownership | principal, session, claim service; tentative 0003 mandatory owner FKs/indexes, legacy quarantine | Session bootstrap/refresh/revoke; owner-scoped book detail; claim DTO issued only by verified account adapter | Secure HttpOnly/SameSite cookies, CSRF and origin checks; hashed tokens; 7-day idle/30-day absolute; claim locks source and target, rotates token, invalidates old authority; no invented users | Forgery, expiry, revocation, cross-owner reads, concurrent claims, stale credentials; PG owner isolation before private API |
| 3 Catalog / templates | product/template/version/variant and per-version personalization schema; tentative 0004; immutable published revisions and asset FKs | Public product list/detail/template versions; quota-free preview; explicit private template-book creation | Agent 2 renders shared documents; publication permissions separate from owner rights; preview read-only/no private Book, bounded/rate-limited; save uses validated version snapshot and idempotency | Deterministic browser -> API -> PG -> reopen, invalid choices, Unicode, preview no Book/quota; first real frontend vertical slice |
| 4 Manual editor | editor service; additive revision/cover/dedication schema only after contract review | Manual create; expected-revision patch, insert/delete/reorder/duplicate and cover/dedication DTOs | Owner check in transaction; one revision per complete edit, rollback all rows; duplicate gets new UUID and clears source-page identity; source remains immutable | Lost-update races, reorder/deletion/duplication, size bounds, authorization and immutable source; no partial revision |
| 5A Durable jobs foundation | operations/idempotency/attempt journal/encrypted snapshot/outbox; tentative 0005 | Internal fake-worker contracts only initially | Agent 1 contract 66732fc; frozen admission policy; fencing/lease and crash recovery; no dispatch before M6 | Crash/lease races, unknown dispatch never resent, storage-only accepted-finalization recovery; queue TTL/lease/recovery settings require approval |
| 6 Quotas / abuse | daily capability buckets/reservations/dispatch guards; tentative 0006 | Safe quota summary; rate-limit envelopes, no raw abuse signals | UTC dates, separate 10 story/10 image; first dispatch authorization durably consumes once with attempt journal; release only proven pre-dispatch and all dispatchers fenced; principal/claim locks prevent rotation reset | PG simultaneous admissions, midnight, idempotency, uncertain attempts, claim aggregation, distributed process races; no per-pod authority |
| 5B Async activation | compose API/worker with real quota adapter | POST /v3/jobs/stories -> new 202; same-key replay 200 OperationStatus; poll/cancel owner-scoped; sync AI route separately reviewed | Same owner/capability cross-route idempotency; >=48h terminal replay; accepted source + Book + operation completion atomic; engine/projection delegated to Agent 1 | Fake-only HTTP/PG lifecycle, cancellation, quota accounting, failures never completed; real dispatch remains separately gated |
| 7 Integrated verification | API integration fixtures/browser harness; migration matrix | Published reviewed v3 OpenAPI; existing v1/v2 unchanged | Agents 1/2/4 agree integration base; no mock ownership/quota adapters in deployed path | Full offline suite, real PG API/races/recovery, browser save/reopen; capacity and security evidence recorded |

Template schemas must version approved editable fields: name, age_months, language, dedication and
explicit appearance choice IDs (for example hair, skin, glasses, freckles, clothing). No inferred
traits, universal child profile table, date-of-birth collection or arbitrary unvalidated JSON.
Publication and asset rights require editorial review. Covers/dedications use typed roles in a
future contract and never silently change requested AI story-page count.

## Milestone 8: verified accounts and lifecycle

Modules: identity adapter, account/claim/privacy application services. Migration: accounts,
verified external identity unique(provider, subject), verification challenges and account-principal
relationship; encrypted contact data only where needed. Google/email verification is an adapter
boundary, not trusting client-supplied email. Endpoints: verified sign-in callback/challenge,
account session, explicit claim, revoke-all and deletion request. DTOs exclude credential material.
Anonymous browsing/creation remains supported. Claim requires simultaneous proof of both identities,
locks ownership/quota namespaces, preserves original usage and makes old sessions ineffective.
Idempotent claim/deletion commands must survive retries. Dependencies: M2, security/key/retention
approval and Agent 2 login/guest UX; Agent 1 jobs must obey claim/revocation fences. PG tests cover
unique identity races, claim/replay, revoked access, deletion versus active jobs. Acceptance: no
email-only takeover, no public account enumeration and documented backup/deletion semantics.

## Milestone 9: commercial catalog and prices

Modules: catalog/pricing; migration: product_variants, price_versions and publication policy,
FKs to products/templates, immutable price revisions. Public endpoints list variant options and
server-authoritative quote DTOs (integer minor units, currency, expiry/version). Editorial writes
require separate admin authorization. Configurations select allowed creation modes and template
versions; client prices are ignored. Concurrent publication is transactional and idempotent.
Dependencies: M3, Agent 2 product selectors, approved actual currencies/tax/discount policies;
Agent 1 has no pricing authority. PG tests cover price/version races and unsupported variants.
Acceptance: deterministic fixtures work without inventing live commercial rates.

## Milestone 10: durable guest/account carts

Modules: cart service/repository; migration: carts, cart_items, configuration snapshots and unique
command keys, owner FK and expiry indexes. Endpoints: get cart, add/update/remove item and claim;
DTOs include variant, quantity, configuration digest, book/revision reference and server quote.
Two differently personalized copies must remain distinct even with the same variant. Guest preview
alone never creates a Book; explicit save/add-to-cart may instantiate one transactionally after
validation. Authorization uses M2 owner; account claim is M8 compatible. Add command idempotency
and revision CAS prevent duplicate items/lost updates; price always recomputed server-side.
Dependencies: M3/4/9 and Agent 2 cart UI. PG tests: guest persistence, cross-owner access, distinct
copies, stale edits, concurrent add/claim. Acceptance: reopen cart with correct private copies.

## Milestone 11: guest checkout and immutable orders

Modules: checkout/order services with policy ports; migration: checkouts, orders, order_items,
minimal encrypted customer/shipping snapshots and immutable monetary breakdown/version fields.
Endpoints: validate checkout, create order, retrieve confirmation; DTOs include server totals and
safe status only. Guest checkout uses existing owner plus explicit verified order-access proof
when recovering access; an order UUID/email alone is insufficient. Freeze selected Book revision
or immutable print snapshot, variant/configuration, quantity, unit prices, currency, taxes,
discounts and shipping quote/policy versions in one idempotent transaction. Expired quotes require
explicit reconfirmation, never silent client-price acceptance. Dependencies: M9/10, approved tax,
discount/shipping and data-retention policies, Agent 2 checkout. PG tests cover replay/races,
repricing, immutable snapshots and PII-safe errors. Acceptance: deterministic unpaid order with
correct immutable totals; no real shipping rates or payment call.

## Milestone 12: fake payment boundary

Modules: payment port and fake adapter; migration: payment_attempts, provider_event_inbox,
order transition/outbox records with unique event/command IDs. Endpoints: fake checkout payment
command, safe payment status; future provider webhook contract requires signature verification.
Only owner/admin operations allowed; external events must be verified independently. Atomic event
deduplication and order transitions prevent duplicate charges/state changes; durable outbox avoids
transaction/external-call coupling. No card data, raw secrets or live provider integration.
Dependencies: M11, separate provider approval and Agent 2 result UI. PG tests simulate repeated,
out-of-order and concurrent success/failure events. Acceptance: fake payment confirmation and
retry-safe order state, never a claim of real payment processing.

## Milestone 13: fulfillment, history and shipment boundaries

Modules: fulfillment/shipping/notification ports with deterministic fake adapters; migration:
fulfillment_jobs, shipment references/status history, deduplicated events and outbox. Endpoints:
owner order history/detail, safe shipment status; admin fulfillment commands separately scoped.
Address access limited to authorized fulfillment, no PII in event logs. Lock expected order state,
write event/outbox once, process retries idempotently; never send email/messages without explicit
authorization. Dependencies: M11/12, Agent 2 tracking UI, separately approved real vendors.
PG tests: history isolation, duplicate/out-of-order updates, cancellation races. Acceptance:
fake end-to-end confirmation/history/fulfillment; no real shipment booking or quoted live rates.

## Milestone 14: production readiness gate

Modules/migrations as approved for retention/deletion audit metadata, encryption-key versioning,
backup restore and access control. Endpoints only for reviewed export/deletion/admin operations.
Dependencies: privacy retention decisions, operational ownership, threat review, merchant policies
and Agents 1/2/4 integrated verification. Test real PostgreSQL restore/migrations, least privilege,
redacted logs, key rotation and deletion across books/assets/orders/jobs/backups. Acceptance requires
explicit deployment approval, documented incidents/monitoring and jurisdiction-specific policy review.
This roadmap does not authorize production access, live payments, cloud keys or deployment.

## Delivery slices and decisions

First deterministic real frontend/API/PostgreSQL slice: M3 after M2 security, using a seeded public
catalog, personalization preview, explicit save and private reopen. M1 alone is internal persistence,
not a completed frontend workflow. Second commerce slice: M9-13 with fake pricing fixtures/payment/
shipping ports, from product selection to cart, checkout, confirmation and history.

Remaining approvals: integration base and milestones 2 onward; precise abuse/rate thresholds;
account verification adapter; encrypted snapshot key management and child-content retention;
queue/lease/finalization recovery settings; cover/editor contract; supported currencies and tax/
discount/shipping policies; catalog licensing; real providers and production release. Existing UTC,
10+10 quotas, durable first-dispatch consumption, proven-unsent release, >=48h terminal replay,
7-day idle/30-day absolute sessions and quota-free guest previews are the design defaults.
