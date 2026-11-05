# StoryForge QA test matrix

Evidence date: 2026-11-05. This matrix separates actual tests from specifications.
P0/P1/P2 follow QA_STRATEGY.md. Each row is a scenario group, not a test count.
Passed rows refer to this QA execution unless explicitly described as external
handoff evidence. Planned rows are not pytest skips. No v3 contract is approved yet.

| ID / feature | Scenario | Level | Priority | Automation status | Dependencies | Actual execution status |
| --- | --- | --- | --- | --- | --- | --- |
| AI-01 length | 1/6/27/32 pages across ages/he/en | Graph + Fake | P0 | Implemented and passed | Existing v2 execution suite | Passed in full QA run |
| AI-02 length | Fixed seven pages at 0/2/3/11/12/35/36/71/72/10000 months | HTTP + Fake | P0 | Implemented and passed | test_qa_v2_http.py | Passed |
| AI-03 structure | One-based contiguous pages, unique IDs and declared count | Domain/graph/HTTP | P1 | Implemented and passed | Existing v2 and QA tests | Passed |
| AI-04 alphabet | Roy 27-page Hebrew ordered base/final-form targets | HTTP + Fake | P1 | Implemented and passed | Committed Roy fixture | Passed, structural only |
| AI-05 education | Generic ordered concepts; reject wrong/missing/reordered assignments | Gate + HTTP | P1 | Implemented and passed | Existing v2 and QA mutations | Passed |
| AI-06 languages | Hebrew niqqud/logical order, accented names, emoji, RTL/LTR metadata | HTTP + Fake | P1 | Implemented and passed | Five QA regression fixtures | Passed; he/en only |
| AI-07 stories | General/bedtime/adventure/educational/alphabet shape | HTTP + Fake | P1 | Implemented and passed | QA fixtures and v2 tests | Passed; not semantic compliance |
| AI-08 validation | Missing/auto/string/bool/fraction/nonpositive/excess pages | HTTP + Fake | P0 | Implemented and passed | Empty provider script | Passed, zero calls |
| AI-09 input | Strict age, unsupported language, bidi/unknown private fields | Domain/HTTP | P1 | Implemented and passed | Existing + QA suite | Passed, sanitized failures |
| AI-10 failure | Refusal/unavailable/unsafe output | HTTP + Fake | P0 | Implemented and passed | Scripted FakeStep errors | Passed, no story |
| AI-11 recovery | Malformed/short books and failed quality rewrite | Graph/HTTP + Fake | P0 | Implemented and passed | Scripted plan/writer | Passed, bounded attempts |
| AI-12 limits | Attempt/token/input/cost reservation admission | Graph/accounting | P0 | Implemented and passed | Existing engine/accounting/v2 tests | Passed |
| AI-13 timeout | Fake latency and actual async timeout/overall deadline/cancel | Graph/HTTP | P0 | Implemented and passed | Existing engine/API + QA tests | Passed; no remote cancellation proof |
| AI-14 upstream | 429/503 mapping, hidden SDK retries absent | Adapter + mocked HTTP | P0 | Implemented and passed | Existing Gemini provider tests | Passed, no vendor contact |
| AI-15 accounting | Unknown token/cost values stay unknown | Accounting/graph | P0 | Implemented and passed | Existing real-accounting + QA | Passed, no invoice guarantee |
| AI-16 recovery | Transient planner error -> planner/writer succeeds in three calls | HTTP + Fake | P0 | Implemented and passed | New QA regression | Passed in final focused run |
| AI-17 isolation | Simultaneous he/en child names, counts, UUIDs and ledgers stay separate | HTTP + local fixture provider | P0 | Implemented and passed | New QA concurrent regression | Passed in final focused run |
| AI-18 quality | Coherence, agency, suitable repetition and age fit | Human editorial | P1 | Planned only | Native reviewers/manuscripts | Not executed; rubric provided |
| AI-19 teaching | Final forms, examples, factual accuracy | Human editorial | P1 | Planned only | Native educator/editor | Not executed; literal inclusion insufficient |
| AI-20 diagnostics | Upstream categories/statuses, safe attempt metadata and stop reasons | Adapter/engine/API with mocked HTTP | P0 | Implemented and passed | Pinned Agent 1 snapshot | 42 tests passed; not merged into QA baseline |
| FE-01 foundation | Forms/client parser/hooks/RTL/cancellation | React/jsdom + mocks | P1 | Implemented and passed | Committed frontend snapshot | 40 tests passed |
| FE-02 build | Strict TS and production bundle | Build | P1 | Implemented and passed | Copied installed dependencies | Build passed; npm ls passed |
| FE-03 layout | Landing 320/390/768/1440 and Hebrew mobile reader overflow | Real Chromium/mock service | P1 | Implemented and passed | QA browser runner/snapshot | Passed |
| FE-04 navigation | Explicit count after age edit, reader start/end | Real Chromium/mock service | P1 | Implemented and passed | QA browser runner | Passed |
| FE-05 direction | English UI/Hebrew story, switch UI to RTL, niqqud preserved | Real Chromium/mock service | P1 | Implemented and passed | QA browser runner | Passed |
| FE-06 accessibility | Skip-link keyboard activation, error announcement and invalid-field focus | Real Chromium/mock service | P1 | Implemented and passed | QA browser runner | Passed; partial accessibility evidence |
| FE-07 cancellation | Cancel delayed demo, retain brief, no stale reader | Real Chromium/mock service | P1 | Implemented and passed | QA browser runner | Passed |
| FE-08 injection | HTML-like name renders as text, no img node | Real Chromium/mock service | P0 | Implemented and passed | Synthetic inert payload | Passed |
| FE-09 refresh | Unsaved brief discarded, no local/session storage | Real Chromium/mock service | P1 | Implemented and passed | Current explicit demo contract | Passed; not persistence |
| FE-10 states | Demo error and empty-reader recovery | Real Chromium/mock service | P1 | Implemented and passed | Demo-state controls | Passed; not real network failure |
| FE-11 API | Form -> real local Fake API -> approved reader | Browser/API integration | P0 | Prepared but blocked | Reviewed HTTP-service selection/origin composition | Not executed; app imports only mock service |
| FE-12 failure | Real 422/503/504, malformed response, network loss, explicit retry | Browser/API integration | P0 | Prepared but blocked | Same as FE-11; controlled fault injection | Not executed; mocked fetch tests are separate |
| FE-13 a11y | Screen reader, contrast, zoom/reflow, full keyboard audit | Human + browser | P1 | Planned only | Reviewers, approved UI | Not executed |
| FE-14 storefront | Navigation/history/product discovery/details/filter states | Browser/catalog | P1 | Prepared but blocked | Agent 2 product UI + approved catalog API | Not executed; unfinished/uncommitted work excluded |
| FE-15 library | My Books list/read/reopen/empty/error states | Browser/API/DB | P0 | Prepared but blocked | Common Book API + persistence + ownership | Not executed |
| TP-01 catalog | Listing/filter combinations/bounded stable cursor pages | API/DB/browser | P1 | Prepared but blocked | Agent 3 approved catalog contracts | Specification only |
| TP-02 details | Localized product detail and ordered public previews | API/browser | P1 | Prepared but blocked | Eligible releases/public assets | Specification only |
| TP-03 schema | Different fields/defaults/options for two products | Renderer/unit/UI | P1 | Prepared but blocked | Approved personalization schema/control registry | Specification only |
| TP-04 validation | Missing required, optional default, unknown key, invalid choice/oversized value | Contract/API | P1 | Prepared but blocked | Exact approved schema | Specification only |
| TP-05 render | Exact substitution, missing/unknown placeholders, he/en/RTL/Unicode | Pure renderer | P0 | Prepared but blocked | Approved renderer/document schema | Specification only; no invented parser |
| TP-06 safety | Expressions/HTML/attribute injection treated safely | Renderer/browser | P0 | Prepared but blocked | Safe placeholder/content model | Specification only |
| TP-07 version | Draft/published/retired eligibility, immutability and publication races | PostgreSQL/service | P0 | Prepared but blocked | Migrations after 0001/publication logic | Specification only |
| TP-08 snapshot | Existing Book unchanged after new release/version | API/DB/browser | P0 | Prepared but blocked | Source pinning/common Books | Specification only |
| TP-09 assets | Missing/blocked/private asset references rejected, no partial save | API/DB | P0 | Prepared but blocked | Asset model/access resolver | Specification only |
| TP-10 parity | Same version/variant/choices yields identical preview and saved content | API/DB/browser | P1 | Prepared but blocked | Shared renderer and approved creation API | Specification only |
| TP-11 no AI | Template render/save invokes zero providers | Integration | P0 | Prepared but blocked | Implemented template service | Specification only |
| ME-01 draft | Create empty draft, update title/metadata | API/editor/DB | P1 | Prepared but blocked | Approved manual Book API | Specification only |
| ME-02 pages | Add/delete/edit page content and layout, stable page IDs | API/editor/DB | P1 | Prepared but blocked | Document/layout rules and editor | Specification only |
| ME-03 order | Exact page permutation, duplicate/missing/foreign IDs rejected | API/PostgreSQL | P0 | Prepared but blocked | Atomic reorder/constraints | Specification only |
| ME-04 save | Explicit save/reopen retains all content and order | Browser/API/DB | P0 | Prepared but blocked | Save/get composition | Specification only; no autosave assumption |
| ME-05 concurrency | Two editors/stale revision conflict leaves newer write intact | API/PostgreSQL/browser | P0 | Prepared but blocked | Approved revision/ETag semantics | Specification only |
| ME-06 preview | Preview matches saved document | Browser/API | P1 | Prepared but blocked | Shared PageDocument renderer | Specification only |
| ME-07 lifecycle | Empty/invalid finalization blocked; finalized edits blocked | API/PostgreSQL | P0 | Prepared but blocked | Approved lifecycle rules | Specification only |
| ME-08 loss | Refresh before/after save, offline save and ambiguous commit | Browser/API/DB | P0 | Prepared but blocked | Explicit save/network recovery contract | Specification only |
| ME-09 no AI | Manual operations make zero provider calls | Integration | P0 | Prepared but blocked | Manual service | Specification only |
| DB-01 baseline | 0001 upgrade/current/check/rollback/FK/atomic completion | PostgreSQL repository | P0 | Prepared but blocked | QA-owned disposable PG + pinned persistence snapshot | Agent 3 reports 14 PG passes; QA did not rerun |
| DB-02 portability | SQLite transactions and offline PostgreSQL DDL | Repository/DDL | P1 | Prepared but blocked | Persistence dependencies/snapshot absent from QA baseline | Agent 3 reports 9 cases; not independent QA evidence |
| DB-03 atomic AI | Generate -> accepted source + common Book -> reopen after restart | Full local E2E | P0 | Prepared but blocked | AI/Book unit-of-work and approved routes | Not implemented/executed |
| DB-04 failures | Failure/cancel/storage exception produces no Book or partial pages | API/PostgreSQL | P0 | Prepared but blocked | Storage-aware execution composition | Specification only |
| DB-05 transactions | Mid-insert rollback, concurrent lifecycle winner, consistent read | PostgreSQL | P0 | Prepared but blocked | Disposable QA database | Existing Agent 3 cases reported; QA rerun pending |
| DB-06 product schema | Source-mode/FK/revision/template sealing/page order constraints | PostgreSQL migration/service | P0 | Prepared but blocked | Approved product migrations | Design only beyond 0001 |
| DB-07 retry | Idempotency and ambiguous commit handling without regeneration | API/PostgreSQL | P0 | Planned only | Approved durable idempotency contract | Not implemented; no assumed retry guarantee |
| SEC-01 redaction | Dummy secret/provider text and private invalid input absent from public errors/logs | HTTP/provider mock | P0 | Implemented and passed | QA + existing adapter tests | Passed, captured process logs only |
| SEC-02 headers | no-store, server request ID, no failed drafts/plans in failure | HTTP | P0 | Implemented and passed | QA HTTP assertions | Passed |
| SEC-03 access | Unauthorized/cross-user list/book/page/preview/asset denial | API/DB/browser | P0 | Prepared but blocked | Real principal/owner model, not UUIDs | Not executed; release blocker |
| SEC-04 assets | Unsafe scheme/remote URL/path/unauthorized asset rejection | Contract/API/browser | P0 | Prepared but blocked | Approved asset-reference contract | Specification only; no actual hostile fetch |
| SEC-05 minimization | No child data in catalog, logs, analytics/URLs/cache artifacts | Cross-layer security | P0 | Prepared but blocked | Catalog/storage/logging composition | Process-level canaries only verified |
| SEC-06 credentials | Git-history/content secret scan, dependency review | Static/security review | P0 | Planned only | Approved scanner/offline rules | Filename inspection only in earlier handoff |
| SEC-07 retention | Linked source/Book erasure, backups and tenant isolation | DB/security | P0 | Planned only | Approved retention/deletion/ownership | No policy or workflow verification |
| FUT-01 export | Illustration/save/export/print and Unicode pagination | Product integration | P1 | Planned only | Implemented export/illustration contracts | Not executed |

Diagnostics snapshot execution and final aggregate counts are recorded in
QA_HANDOFF.md. Baseline QA does not include Agent 1's additive metadata fields;
cross-branch compatibility requires later approved integration and a new full run.
No row currently claims full browser/API/PostgreSQL E2E success.
