# B1 and confirmed Fake regression handoff

Date: 2026-11-05. Branch: `feature/b1-offline-canonical-projection`.
Scope: user-approved offline canonical AI text projection and QA D-01 fix only.
Broader quality/provider reliability work is documented, not implemented.

## Implemented

- Strict initial canonical AI text-only contracts, distinct from the engine's
  unchanged StoryV2 and Agent 3's future full editable Book aggregate.
- Versioned server-controlled capacity policy: product maximum 32 pages;
  title 120 code points; 128 nonempty units/page, 400 code points/unit;
  262144 bytes/document and 16777216 bytes/complete projected BookDetail.
- Conservative pure pre-generation admission and exact actual compact UTF-8
  size validation, including all wrappers/nulls/provenance. No truncation or
  automatic density/page-count change; UTC initial timestamps are enforced.
- Lossless accepted-source projection, exact N/order/units/targets, he RTL/en LTR,
  independent canonical page UUIDs, contextual source revalidation and deterministic
  gate/version checks. No cover, dedication, illustration or asset support in B1.
- Trusted backend ownership assertions are checked for matching issuance owner
  and verified scope; this does not implement credentials/authentication or prove
  cryptographic source provenance.
- D-01 fixture correction: actual word-gap distribution, no punctuation-only
  entries, exact multiword name/label preservation and unchanged density limits.
  Original reproduction now succeeds in two engine attempts. Unsupported minimal
  fixture combinations fail explicitly and nonretryably, without a partial book.

## Changed files

| Files | Purpose |
| --- | --- |
| `src/storyforge/projection/__init__.py`, `contracts.py`, `capacity.py`, `service.py` | New offline contracts, policy, admission, validation and projection |
| `src/storyforge/llm/fixtures_v2.py` | Confirmed deterministic Fake distribution fix |
| `tests/test_projection_contracts.py`, `tests/test_projection.py` | Strict/Unicode/byte/age/language/target/provenance/identity/source boundaries |
| `tests/test_fixture_density.py` | Original D-01 and multiword/whitespace/unit/density regressions |
| `README.md`, `docs/PHASE_B1.md` | Implemented scope, module boundaries and limitations |
| `docs/QUALITY_REMEDIATION_PLAN.md` | Evidence-based quality priorities; proposed checks/evaluation only |
| `docs/LONG_BOOK_RELIABILITY_ASSESSMENT.md` | Actual offline normalization bounds and unapproved controlled evaluation proposal |
| This handoff | Completion evidence and remaining dependencies |

No committed changes to graph, SDK adapters, API routes, settings, developmental
profiles, prompts, quality rules, dependencies or example runtime/request files.
No database/migration, jobs, auth, frontend, commerce or production integration.

## Reviewable commits

| Commit | Change |
| --- | --- |
| `32cbf57` | B1 strict contracts and capacity policy |
| `a9858f8` | Admission/projection, deterministic tests and B1 documentation |
| `6d4b5c0` | Confirmed Fake density regression fix and tests |
| `348bbde` | Quality remediation assessment |
| `8405216` | Long-book capacity/reliability assessment |
| `5194484` | Follow-up: reject non-UTC updated_at even when it represents the same instant |

The final documentation-only handoff commit follows these; see git log.

## Offline verification

Python 3.13.3, pytest-socket network guard. Numbers overlap; do not add them.

| Check | Result |
| --- | --- |
| Initial contract suite | 25 passed, 0 failed |
| B1 projection/contracts + existing v2 contracts, before Fake fix | 269 passed, 0 failed |
| Fake regression + existing v2 execution/API, after fix | 169 passed, 0 failed |
| Full clean suite at `6d4b5c0` | **968 passed, 0 failed**, 270.36 s |
| Final clean B1 projection/contracts at `5194484`, including UTC follow-up | **153 passed, 0 failed**, 23.13 s |

D-01's new corrected-expectation test first failed before the fix with measured
16 rather than 15 words; it then passed. No failure was hidden by relaxing density.
The final UTC change received its meaningful new contract regression and the full
B1 subset; the full 968-case run predates that two-line guard, explicitly above.

During completion, additional uncommitted quality-related changes appeared in
the shared working tree. They were preserved and excluded from all our commits.
A working-tree suite also passed 975 cases, but it includes those separate edits
and is not used as isolated acceptance evidence for this work. Clean verification
used our own ignored `.tools/b1-offline-verification` detached worktree, with its
src placed first on sys.path before invoking pytest. No other agent worktree was
modified. Do not attribute the pending quality-version/advisory changes to B1.

Equivalent normal commands for these suites from a checkout with this source:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_projection.py tests/test_projection_contracts.py tests/test_v2_contracts.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_fixture_density.py tests/test_v2_execution.py tests/test_api.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

Also checked Markdown local links/fences/UTF-8, staged whitespace and source diff
scope. Recomputed N=1..32 normalization for both languages/densities/all bands
using unchanged default and isolated Roy settings, without credentials/providers.

## Remaining dependencies and stop boundary

Agent 3 must integrate/reuse or relocate the reviewed initial projection types
into its eventual canonical model, supply verified ownership/source correlation,
preserve this serializer/capacity proof, and derive its private source snapshot.
No competing editable Book store or shared v3 API DTO implementation was created.
Persistence/access/jobs/encryption and frontend remain separate approvals.

Canonical 32-page representation does not imply runtime readiness. Isolated Roy
Planner allows at most 29 pages; Hebrew density can impose lower Writer bounds.
N=32 needs 3272 Planner tokens against cap 3000. The 27-page upstream Writer 503
root cause remains unknown. No chunking, fallback, extra attempts or higher caps.

Incorrect educational metadata, contradiction, gibberish and excessive repetition
remain quality limitations demonstrated by synthetic QA witnesses, not evidence
about live Gemini outputs. Reviewed Hebrew education packs, natural-language and
full-book semantic/editorial evaluation require separate approval. No broad
quality-engine or prompt change is committed by this work.

No live AI calls, credentials/environment modifications, merge, push or deployment.
Stop here for review before broader quality changes or any live evaluation.
