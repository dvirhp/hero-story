# StoryForge AI comprehensive QA strategy

Prepared 2026-11-05, independent Agent 4 QA branch. This is a test strategy for
the three-mode product vision, not a claim that the three modes are implemented.
See [execution matrix](QA_TEST_MATRIX.md), [handoff](QA_HANDOFF.md) and the separate
[human review rubric](QA_HUMAN_REVIEW.md).

## Evidence and contract authority

AI v2 is executable on QA baseline `5ae24e9`: strict explicit page count, he/en,
sentence_units, ordered targets, bounded engine and sanitized HTTP failures.
The QA branch adds tests only. Source contracts and OpenAPI take precedence over
this strategy. Current global-language aspiration does not imply implemented
support beyond Hebrew and English.

Inspected Agent 1's committed `docs/PROVIDER_DIAGNOSTICS.md` at `7105be9`, Agent 2's
`docs/FRONTEND_HANDOFF.md` at `c2b72c2`, and Agent 3's
`docs/PERSISTENCE_HANDOFF.md` at `73ac933`. Agent 3's new DATABASE_SCHEMA.md and
API_CONTRACTS.md were read as mutable, uncommitted proposals. The latter explicitly
supersedes the older save=true suggestion with proposed v3 Book endpoints.
Neither proposal is an approved executable contract. Do not write asserted v3
payloads/status mappings, migrations or product implementation from those drafts.
Re-read the approved revision when available and pin its commit before automation.

The inspected frontend is a mock-service React foundation; no catalog, template
creation, editor or library is committed there. Persistence has a repository and
revision 0001 for accepted AI source stories, not a common Book product workflow.
No merge/cherry-pick or product feature implementation is part of QA preparation.

## Test architecture and truthful reporting

| Level | Real components | Substitute / boundary |
| --- | --- | --- |
| Pure contract/quality tests | Pydantic contracts, normalization, profile configuration, deterministic gate | Synthetic structured text; no semantic judge |
| Graph/HTTP integration | FastAPI ASGI transport, dependency/lifespan/cancellation, LangGraph, ledger, gate | FakeProvider scripted results; no TCP server or DB |
| Provider adapter contracts | Real adapter/SDK serialization and response handling | Mocked HTTP transports and dummy keys; no vendor network |
| Frontend component tests | React, form logic, client parser, hooks in jsdom | Mock service/fetch; no real browser/server integration |
| Browser component journey | Real headless Chromium, built React app on loopback | App's editorial sample service; no API or database |
| Repository integration (future QA rerun) | SQLAlchemy/Alembic and disposable local PostgreSQL | Fake engine outputs only; SQLite results reported separately |
| Full local E2E (blocked) | Browser -> approved API composition -> Fake engine -> PostgreSQL -> reopened reader | Only AI replaced; all application/storage communication real |
| Human editorial review | Complete manuscripts read aloud by native-language adults | No automated metric substitutes for judgment |

Each result records source SHA, command, environment, test count, elapsed time when
available, substitutions, actual status and dependencies. Use exactly
Implemented and passed, Implemented but failing, Prepared but blocked, or Planned
only in the matrix. Blocked means prerequisites are missing; it is not a pass or a
fabricated pytest skip. Findings include expected/actual behavior and a minimal
test command; store only synthetic, sanitized evidence. Keep historical reports
separate from independently executed results. Do not sum overlapping focused runs
as distinct coverage. No line/branch coverage percentage is claimed without data.

## Risk priorities

P0 blocks release: private-book/asset disclosure, credential leakage, executed
untrusted markup/placeholders, unbounded provider execution, rejected/partial book
published, lost or cross-user data, or false saved-success after failed commit.
P1 blocks the affected journey: wrong explicit page count/target order, migration
loss, stale overwrite, template version drift, broken RTL, inaccessible required
controls or unrecoverable save/network behavior. P2 includes presentation defects
that do not prevent use; evaluate individually rather than hiding them in averages.

Product risks remain open even without a confirmed defect: no ownership/auth model,
retention/erasure policy, common Book API, template renderer or editor implementation.
Local synthetic-only execution is the available boundary; UUIDs are not access control.

## AI generation

Cross explicit counts 1, 6, 27 and 32 with both languages, both densities, five
age profiles, adjacent month boundaries and open-ended older age. Check exact count,
unique stable IDs, contiguous one-based order and requested count unchanged after
age edits. Assert no silent clamp, padding or partial success. Roy's committed
27-target Hebrew fixture is the structural acceptance case, not an educational
manuscript. Preserve final-form metadata and target order on all recovery paths.

Exercise planner/writer schema errors, incomplete books, malformed JSON, extra
fields, names absent, script mismatch, terminal unsafe output, refusal, 429/503,
network failures, attempt timeout, overall deadline, cancellation, quality rewrite,
input/token/cost reservations and exhausted capacity. Assert ledger/call counts,
unknown usage remains unknown, one shared attempt budget and no failed draft in
response or storage. Upstream HTTP 429/503 differs from the application's 503;
only diagnostics with actual upstream evidence may identify a vendor status.

Use FakeProvider for deterministic product regressions and mocked transports for
SDK behavior. Never set a real key, load .env, enable tracing, or start a configured
vendor factory. Fake deadlines and mock status codes do not prove remote behavior.
Native reviewers assess coherence, agency, suitable repetition, age fit and facts
using QA_HUMAN_REVIEW.md; automated word/script/target checks establish none of them.

## Template-based journey specifications

Once Agent 3's contracts and publication model are approved, create original
synthetic editorial fixtures: two products with different required/optional fields,
one Hebrew and one English release, two immutable versions of one template, draft,
published and retired states, valid/missing/blocked assets, and finite page variants.
Do not copy competitor manuscripts. Exact field IDs and DTOs come from the approved
template schema, not these scenario labels.

Catalog tests cover listing/filter intersections, bounded pagination, stable order,
missing localization and hidden/retired products. Detail/preview tests ensure only
cleared public sample assets and no private child content. Schema-driven controls
must render each product's field types/defaults/options, reject absent required,
unknown/oversized fields and invalid choices, and preserve optional defaults.

Renderer tests preserve literal names, Unicode and logical order; missing or unknown
placeholders fail safely. Test nested/expression-like placeholders, HTML/script text,
attribute/URL injection and prototype-like keys as data, never executable code.
Use approved pure rendering contracts before asserting substitution semantics.

Compare preview and saved pages for the same pinned version/variant/choices. Save
atomically, update the catalog release, and reopen the older book: content, source
version and assets must stay stable. Test publication/instantiation races, missing
assets and rollback without orphan books. Retirement hides new creation without
silently rewriting an existing book. All remain specifications until implemented.

## Manual editor journey specifications

Start a blank draft, edit title, add/edit/delete/reorder pages and layouts, explicitly
save, reopen and compare stable page identities/content/order. Follow approved rules
for an empty draft versus finalization; test delete-last-page and exact reorder
permutations. Never assume autosave, localStorage or cloud persistence exists.

Use two browser contexts for competing edits. The approved version/ETag contract
must reject a stale write without overwriting newer data; UI retains unsaved text
and offers an explicit recovery path. Test refresh before/after explicit save,
offline/save errors, retry after ambiguous commit and reopening in a fresh context.
Provider calls must remain zero for manual/template creation. Preview must match
saved documents and finalization must reject incomplete or invalid states atomically.

## Browser, integration and accessibility

Maintain semantic selectors (labels/roles) and immutable synthetic scenarios.
`qa/e2e/browser-regression.mjs` exercises the committed demo in a real browser;
it blocks non-local requests, records no screenshots/video/traces and verifies no
v1/v2/v3 API requests occur. It tests responsive landing, keyboard skip activation,
form error focus, exact count, reader boundaries, Hebrew metadata/logical text,
cancel/stale result, HTML-like text and explicit no-save refresh behavior.

When the HTTP service is actually selected by reviewed frontend composition,
add browser -> local fake API tests with no fetch interception. Verify exact JSON,
correlation, loading/cancel, localized safe error/retry, no automatic generation
retry, network disconnect and malformed response. When storage is connected, read
after save in a fresh process/context and verify PostgreSQL rows; a reader shown
from memory is insufficient. Do not patch the QA frontend to silently enable HTTP.

For all three future modes: storefront navigation/history, discovery, product detail,
personalization, preview, reader and My Books library at 320/390/768/1440 widths;
Hebrew UI/English book and inverse; empty/loading/error states; keyboard-only
submission, visible focus, accessible names, heading order and screen reader review.
Refresh/history tests follow implemented routing contracts. Automated DOM checks
and overflow tests are not a complete WCAG audit; manual screen-reader, contrast,
zoom/reflow and native-language review remain required.

## Persistence and API integration protocol

Coordinate through pinned handoffs and approved interfaces without editing Agent 3's
code. Export a committed snapshot into ignored QA space for independent tests;
never run destructive migration tests on the agent's existing volume or database.
Use a new QA-owned disposable database with explicit local host/database-name
guards, synthetic data only, no SQL echo or DSN/error-object logging, and cleanup
in finally. Installation may need network; ordinary engine tests remain offline.

Run upgrade/current/check and round-trip downgrade/re-upgrade only on that disposable
database. Verify real PostgreSQL FK/unique/check/transaction behavior, ordered reads,
conditional state transitions, concurrent winners, locked consistent snapshots,
rollback mid-page insertion and failed/rejected content exclusion. SQLite/offline
DDL compilation is supplementary and never PostgreSQL runtime evidence.

For future common Books, test source-mode invariants, immutable template versions,
page IDs/contiguous order, atomic AI source+Book completion, stale revision conflicts,
finalization and archive restrictions, pagination/filter isolation, concurrent writes
and DB failure before/during/after commit. Idempotency is not implemented: do not
assert safe automatic POST retries; ambiguous commit must not trigger regeneration.
Exact endpoints/DTOs/status codes wait for Agent 3 approval. Authenticated owner and
asset access predicates are mandatory before cross-user release tests can pass.

## Security fixtures and negative cases

Use two synthetic adult principals only after authentication exists; test missing,
expired and other-user credentials, guessed UUIDs, list/page/preview/asset access and
equal missing/inaccessible responses. Reject malicious field names, unexpected nested
properties, overlong values, invalid Unicode controls, script markup and unsafe media
references. Include file:, javascript:, data: and remote/internal-network URL values
as rejection cases only where an approved asset contract accepts/rejects references.
No actual remote fetch, production probing or destructive security activity.

Canary values in child names, themes, guidance, provider error text and dummy secrets
must not appear in errors, logs, analytics, URLs, cache artifacts or public catalog
projections. Inspect authorized response fields separately: approved story text may
contain its own child's exact name, but never another request's content. Stored
personalization and educational targets are sensitive even without a birth date.
Secret scanning of Git content/history, infrastructure logs, backups, retention,
erasure and browser storage policies require dedicated release checks; existing
canary tests are not a comprehensive privacy certification.

## Recommended release-readiness gates

1. Approved mode/domain/API/template/editor contracts, configured limits and ownership,
   retention/deletion and asset policies; no implementation based on mutable proposals.
2. All applicable deterministic regressions pass; zero unresolved P0/P1 findings.
   Blocked critical journeys remain release blockers, never waived as test passes.
3. Real local browser -> Fake API -> PostgreSQL save/reopen passes for each mode,
   both languages and failure/rollback/conflict scenarios; reproducible pinned evidence.
4. Disposable PostgreSQL migration/rollback rehearsal and security/ownership tests pass;
   no real child data until those boundaries exist and are reviewed.
5. Native-language editorial review of full representative manuscripts, educational
   correctness and read-aloud suitability; agreed human thresholds and recorded concerns.
6. Keyboard/screen-reader and responsive checks, safe runtime logging, secret scanning
   and explicitly verified no-vendor-call default. Illustration/export remains outside
   readiness claims until its own implementation and validation exist.

Current evidence supports local foundations only, not a complete product release.
