# Proposed second Gemini test: רועי וגיבורי ממלכת האותיות

> Superseded implementation approach: use [explicit-length v2](../../PAGE_COUNT_V2.md) and its v2 request/runtime. The age-profile override and v1 request here remain historical planning artifacts; do not use them for the new test. No new live request is approved.

**Status: preparation only; not ready to execute through the default configured API.** No second live request, credential read, billing change, application-code change or Milestone 7 work was performed. The first newborn smoke test's configuration and packaged profiles remain unchanged.

## Prepared files

| File | Meaning |
| --- | --- |
| [request.he.json](request.he.json) | Exact proposed `StoryRequest`, validated against the current schema; Hebrew brief, name רועי, age 36 months, 375-character guidance |
| [requirements.json](requirements.json) | Page-by-page acceptance specification: 22 standard letters followed by five final forms; **not an API payload or currently enforced schema** |
| [profiles.proposed.json](profiles.proposed.json) | Full isolated configuration snapshot, version `development-alphabet-proposed-v1`; only the Hebrew preschool requirements differ from the defaults |
| [runtime.proposed.json](runtime.proposed.json) | Validated proposed Gemini runtime/token/cost/deadline settings; **not activated** |
| [offline-checks.json](offline-checks.json) | Offline validation and illustrative reservation measurements; zero provider calls |

The exact title and ordered sequence are recorded in the request and acceptance specification:

`א ב ג ד ה ו ז ח ט י כ ל מ נ ס ע פ צ ק ר ש ת ך ם ן ף ץ`

One focus letter means one letter is explicitly taught on each page. Ordinary Hebrew words inevitably contain other letters; banning all other characters would make the story impossible. The five final forms are forms of existing letters, not five additional independent alphabet letters.

**Assumption for approval:** the proposed request explicitly supplies `הוא / אותו / שלו` and masculine-singular agreement. These forms are a proposed choice for this test, not inferred from the name. Approve or change them before any live run.

## Current support and blockers

`StoryRequest` has no `page_count`, `target_letters`, exact title or per-page instructions field. Extra fields are forbidden. All concept requirements fit within its current guidance limit (375 of 500 characters), but guidance is untrusted creative data and cannot override the server's hard profile constraints. Adding `page_count: 27` to the request is rejected.

At **36 months**, normalization selects the **preschool** profile: **6 pages**, **25–45 words/page**, **150–270 words total**, with a simple-goal plot. A standalone `Story` or `StoryPlan` can contain 27 pages: neither output schema has a global six-page maximum. However, `validate_for(brief)` rejects that plan/story against the default profile, and Quality Gate rejects the page-count mismatch. Passing standalone Pydantic validation does not establish profile compliance.

Do not submit the prepared request to the default factory expecting 27 pages. The request itself can validate while the model follows the trusted six-page profile; a resulting six-page story could pass ordinary checks without meeting this test. That would not be an acceptable alphabet-test result. Do not truncate, split into multiple generations, omit final forms, misstate the age, disable validation or reinterpret six pages as 27.

There is no typed `target_letter` in `PageIntent` or `StoryPage`; letter assignment would currently exist only in free text. Output page IDs and numbers cannot establish the educational focus or order.

## Proposed isolated test configuration — approval required

The profile proposal uses **27 pages**, **12–24 whitespace words/page**, **324–648 total**, adult read-aloud and the existing simple-goal strategy/plot contract. Existing soft vocabulary/sentence guidance is retained. The request asks for 2–3 short Hebrew sentences per page. These length/developmental values are initial evaluation hypotheses, not validated standards or new defaults for all three-year-olds.

| Control | Existing newborn smoke | Proposed alphabet evaluation |
| --- | ---: | ---: |
| Model, both stages | `gemini-3.5-flash-lite` | Same |
| Planner output cap, including thinking | 800 | 3,000 |
| Writer/rewrite output cap, including thinking | 800 | 6,000 |
| Input cap per attempt / conservative reservation units | 8,000 | 32,000 |
| Total reservation ceiling | 26,400 | 111,000 |
| Maximum provider attempts | 3 | 3 |
| Maximum quality rewrites | 1 | 1 |
| Per-attempt timeout | 30 seconds | 45 seconds |
| Overall deadline | 90 seconds | 135 seconds |
| Internal USD request ceiling | $0.015 | **$0.075, proposed only** |

The ordinary `AppSettings` defaults are 1,200 planner / 3,000 writer output, 8,000 input, 30 seconds/attempt and 90 overall. Their output caps are also tight for a 27-page Hebrew outline/story plus JSON and thinking. The 800-token smoke caps are not a suitable allocation for this task; caps can produce incomplete JSON rather than a complete story.

Google lists this model's capacity as 1,048,576 input and 65,536 output tokens, with structured outputs. Thus the proposed technical caps fit the declared model capacity, but this is not a guarantee of completion, latency or quality. [Model specification](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite).

**The larger settings are not production changes and are not approved for execution.** Runtime JSON alone is insufficient: the configured factory always loads packaged default profiles. A separately approved evaluation runner would need to load the proposed `DevelopmentConfig` and inject it through the already existing `Resources`/`StoryEngine` seam. No new graph, public endpoint, profile selector or architecture is needed for that isolated wiring. This runner has not been implemented here. Before any call it must assert the normalized profile has exactly 27 pages and the approved version, so the default six-page configuration cannot be used accidentally.

Any future runner must retain `StoryEngine.generate`, full plan/story/context validation, the existing Quality Gate, shared three-attempt budget, disabled SDK retries/continuation/tools, and normal failure envelopes. An input/context/output/deadline failure must stop the generation; do not enlarge limits or retry a new generation automatically.

## Token and cost estimates

No tokenizer, model-list, SDK or generation API was called for this preparation. Approximate normal-path planning assumptions are **5,000–12,000 combined input tokens** and **4,500–9,000 combined output tokens** (roughly 1,500–3,000 planner and 3,000–6,000 writer). Hebrew tokenization, JSON overhead, actual outline lengths and thinking make these uncertain; they are sizing assumptions, not measured usage.

Using the currently published standard-text rates, **$0.30/million input** and **$2.50/million output including thinking**, those assumptions imply roughly **$0.013–$0.027** for an ordinary two-call run. The estimate deliberately uses paid rates; this account's free-tier/billing treatment is not established. [Google pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite).

At the proposed hard token caps, with no cache discount:

- Planner + writer: `(64,000 × $0.30 + 9,000 × $2.50) / 1,000,000 = $0.0417`.
- Planner + writer + one writer recovery/rewrite: `(96,000 × $0.30 + 15,000 × $2.50) / 1,000,000 = $0.0663`.
- A planner-retry path has smaller total output capacity (3,000 + 3,000 + 6,000), so the writer-recovery case is the largest allocation.

The proposed **$0.075** ceiling covers these configured reservations. The original **$0.015** cannot cover the proposed mandatory stages: a 6,000-token writer reservation alone costs $0.015 before input/planner costs. Keeping that budget would cause pre-call budget rejection; do not silently treat the test as free or reduce it to a partial story. Actual billing can differ from configured estimates, especially if metadata/prices change or a cancelled request is billed.

Illustrative offline fixtures produced input reservations of **4,870 planner / 8,633 writer / 15,379 rewrite units**, including the profile, schema and, where relevant, previous draft. These are UTF-8 engineering bounds under the existing policy, not provider token counts. The sample serialized outline/story measured 3,863 / 6,531 UTF-8 bytes; neither byte length nor the repetitive test text predicts real literary quality. Actual output/context may differ; the 32,000 cap is a proposed allowance, not a guarantee every valid prior output fits.

Likewise, the 135-second deadline is an unmeasured evaluation allowance. A single fast newborn run cannot establish long-story performance. On timeout, return the typed failure and available ledger, never partial success or an automatically restarted request.

## What the current gate can and cannot establish

| Requirement | Existing deterministic behavior | Required alphabet-test acceptance |
| --- | --- | --- |
| Exactly 27 pages | Hard page count follows injected profile; default requires 6 | Approve/inject the test profile; verify exactly 27 numbered pages, no omissions |
| Unique IDs / ordered numbering / metadata | Enforced by contracts/context checks | Retain unchanged |
| Word limits | Hard per-page/total whitespace counts | Approve the isolated 12–24 / 324–648 targets |
| Exact requested title | Only title shape/nonempty value is checked | Explicit comparison to the requested title |
| Exact letter sequence, one focus/page | No typed target-letter contract or letter-order check | Compare all 27 pages to `requirements.json`; mere occurrence of a character is insufficient |
| 2–3 short sentences/page | Sentence-word observations are advisory; sentence count is not enforced | Count/review sentences; punctuation heuristics alone do not establish natural Hebrew |
| Roy is the active hero on every page | Plan protagonist must match; story name is checked only once, even in the title | Check each page for active agency, not just name presence |
| Hebrew and absence of unnecessary English | `he`/RTL metadata plus coarse script-ratio check, not full language verification | Fluent review; JSON property names/technical IDs remain transport fields |
| Final forms explained accurately | No educational/orthographic semantic checks | Verify pages 23–27 explain final-position forms of כ מ נ פ צ with correct examples |
| Vocabulary, playful refrain, memorable words, continuous adventure, warm read-aloud style | Non-blocking observations / manual guidance | Fluent adult read-aloud and educational review; assess 27-page length for this child |
| Safety | Narrow directives and Unicode controls only | Retain checks and review context; no complete safety guarantee |

Correct final-form anchors for review are **ך ← כ / מלך**, **ם ← מ / ים**, **ן ← נ / גן**, **ף ← פ / אף**, **ץ ← צ / עץ**. The final character of each example and its intended page position were checked offline. Teaching focus should occur in the narrative, not only a page label. Avoid implying the Hebrew alphabet contains 27 independent letters.

The offline audit deliberately built a 27-page story repeating the same non-alphabet text on every page. With the proposed profile it passed the current gate. This demonstrates that a gate pass alone cannot be reported as success for this educational test. Under an approved isolated run, engine success must remain provisional until a separate 27-row acceptance review passes; if requirements fail, report the test as failed without automatic extra generations. If machine-enforced letter/sentence contracts are required instead, that needs separately authorized implementation, not silent changes in this preparation.

## Verification and approval boundary

Offline checks passed for the request, 375-character guidance, manifest sequence/final examples, complete profile coverage, proposed runtime/capacities, plan/story validation under the proposed profile, default-profile rejection and budget arithmetic. **259 existing contract/development/normalization/quality/settings/accounting tests passed.** Socket blocking was enabled during the planning audit; provider calls were zero. Application source, lockfile, production profiles, original smoke request/configuration and credentials were not modified.

Before running, approval must cover the **isolated 27-page profile**, proposed **$0.075 / token / deadline limits**, explicit pronouns, evaluation wiring and **manual structural/semantic acceptance**. Alternatively, request a separately scoped implementation plan for typed educational constraints. No executable live command is claimed for the unchanged default factory because it would use the wrong profile. No Milestone 7 implementation has started; no live request is authorized by these documents.
