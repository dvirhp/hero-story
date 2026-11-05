# Independent AI engine QA and diagnosis for Agent 1

Date: 2026-11-05. Scope: offline diagnosis only; no engine, prompt, policy or
provider implementation changes. All new content witnesses are synthetic.
No private manuscript, prompt, raw provider error, credential or live artifact
was opened or reproduced. No network AI call, merge, push or deployment occurred.

## Conclusion and evidence boundary

Exact count/order and the tested StoryV2 structural contracts work on the exercised
paths. No production-path page-count/order regression was reproduced. The engine's
deterministic acceptance is substantially narrower than a good, accurate children's
story: deliberately contradictory prose, repeated whole pages, Latin gibberish and
incorrect supplied Hebrew final-form metadata can pass. Those are demonstrated
quality limitations, mostly explicit existing policy, not evidence Gemini produced
such manuscripts and not newly discovered violations of the current gate contract.

One confirmed reproducible defect was found in the **local fixture generator**:
an admitted multiword-name/sentence-unit boundary case produces a punctuation-only
unit, exceeds density and fails after consuming all three attempts. This affects
Fake/local acceptance reliability; it is not established as a live-provider defect.

Tested source: QA branch `feature/storyforge-qa-foundation`, starting at
`735b081805cf01aae206d243a67f9a7218717c27`, engine baseline `5ae24e9`.
Agent 1 inspected HEAD: `49410d0219efcf053a3dd5a8892e6b0c67a48a36`.
Its runtime `src/` has no differences from diagnostics commit `7105be9`; the newer
reliability/integration documents are designs only. Diagnostics were retested in
the existing isolated export of `7105be940c4381fcce2d74813681df6afa631474`.
No agent worktree was modified or branch assembled.

New evidence file: `tests/test_qa_engine_diagnosis.py`, 17 observed-behavior cases.
**A passing diagnostic probe means its observation was reproduced. It does not
mean its intentionally bad story passed an editorial standard.** When fixing an
observation, update the test to assert the intended corrected behavior; do not
preserve an acceptance gap just to retain these characterization assertions.

## D-01 — confirmed defect: Fake fixture violates feasible density/unit constraints

Severity **P2**, local fixture/test reliability. Owner recommendation: Agent 1,
`src/storyforge/llm/fixtures_v2.py:35`, token grouping and sentence-unit construction.

Reproduction in PowerShell from `C:\Users\dvir3\storyforge-qa`:

```powershell
$env:PYTHONPATH = 'C:/Users/dvir3/storyforge-qa/src'
& C:/Users/dvir3/OneDrive/Desktop/heroStory/.venv/Scripts/python.exe -m pytest tests/test_qa_engine_diagnosis.py::test_local_fake_fixture_overshoots_density_at_multiword_unit_boundary -q
```

Steps and measured evidence:

1. Submit the synthetic admitted v2 brief encoded in that test: English newborn,
   one page, two-word name, one educational target, exactly 15 sentence-unit
   entries. Normalization admits it; maximum standard density is 15 words/page.
2. `fixture_steps_v2` fills to 15 whitespace words but keeps the two-word name as
   one atomic list element. Fifteen output entries are sliced from 14 elements.
3. The empty slice becomes a standalone `.` entry. Derived page text now has
   **16 whitespace words**, 15 entries and one punctuation-only entry.
4. `assess_story` rejects density. Through actual `LocalFixtureProvider` and
   `StoryEngine.generate`, the plan succeeds and both writers fail contextual
   validation: **3 attempts**, terminal **BUDGET_EXCEEDED**, writer ledger errors
   **PROVIDER_OUTPUT_INVALID** twice; no story is returned.
5. The same test supplies a typed, gate-passing witness with 15 nonempty entries,
   exactly 15 words and the exact name preserved in joined text. Thus this is a
   feasible machine contract, not merely an inherently impossible brief. The
   witness is not claimed to be good baby literature.

Expected: the deterministic local fixture should satisfy this admitted structural
contract, or explicitly document a narrower capability without manufacturing an
invalid book. Actual: its distribution algorithm creates extra punctuation tokens.

Recommended fix: construct nonempty units against the actual whitespace-word budget
and verify the final joined text/count, including multiword names/labels. Preserve
the exact name/target in derived text and all requested counts. Add boundary tests
for unit count versus atomic tokens, multiword labels and both languages. Do not
raise budgets, change age/page selection, silently reduce units, or alter the gate
to accept the malformed fixture. The current failure envelope is correctly bounded;
the error classification itself is not the defect.

## Reproduced quality concerns — not current-policy violations

Severity denotes product/editorial risk before unattended acceptance, not proof of
how often a live model makes the error. Existing advisory policies must not be
silently changed by a bug fix.

| ID / severity | Reproduction node in test_qa_engine_diagnosis.py | Observed evidence | Recommended action for Agent 1 |
| --- | --- | --- | --- |
| Q-01 / P1 continuity and character facts | test_contradictory_character_facts_can_pass | Both he/en contradictory three-page witnesses return success in two attempts; only generic narrative review is advisory | Add human-reviewed continuity cases and score plan-to-page fact/character consistency; retain a global plan and explicit continuity guidance. Do not claim generic advisory text detects contradictions. |
| Q-02 / P1 education | test_wrong_final_form_mapping_is_not_linguistically_validated | Change the canonical Roy fixture's final-kaf base from kaf to aleph; request still validates and its 27-page Fake book passes | For a reviewed Hebrew alphabet pack, validate canonical label/base/example relationships in declarative language/education data, outside graph logic. Arbitrary caller-provided target semantics need explicit editorial validation. Keep current generic contract versus teaching assurance distinct. |
| Q-03 / P1 older-child variety; age-dependent impact | test_identical_whole_pages_are_accepted_by_documented_policy | Six identical whole pages pass in he/en at ages 0, 36 and 120; one distinct page text, advisory FORMULAIC_PAGE_REPETITION | Review degree and function of repetition by profile; use an age-aware human rubric. Preserve useful baby refrains and current advisory policy unless a product-approved rule changes it. |
| Q-04 / P1 English fluency | test_latin_script_is_not_english_fluency_validation | Dense repeated Latin nonsense passes for English; no SCRIPT_MISMATCH | Treat script ratio as script evidence only. Use native editorial review for grammar/fluency; avoid labeling a script pass as language-quality verification. |
| Q-05 / P2 sentence representation | test_sentence_entry_count_is_not_sentence_grammar | One sentence_units entry containing several grammatical sentences passes a requested 1-entry constraint | Describe it as an entry-count contract. If natural sentence count must be enforced, approve a language-aware policy and exceptions first; punctuation splitting alone is unreliable. |

Reproduce any row using the D-01 command with its indicated node name. Q-01 and
Q-03 are parametrized and execute both languages. All run the actual gate and,
except Q-05's pure gate probe, actual graph with scripted FakeProvider.

These findings agree with documented limitations in PAGE_COUNT_V2.md and
VALIDATION_AND_QUALITY.md: semantic progression, sentence grammar, teaching accuracy,
whole-page repetition, fluency and vocabulary fit are not hard semantic checks.
Do not report them as five new unanticipated engine-code bugs.

## Age, language, personalization and narrative review

The implementation separates user-selected count from profile-selected density,
strategy and soft language targets. Existing v2 tests cross 1/6/27/32 pages, Hebrew
and English, all age bands and open-ended ages. The focused regressions exercise
those paths again and mutate count, ordering, target order and density. Density
is whitespace-delimited engineering measurement; the profiles are provisional,
not scientifically validated developmental standards.

Both languages' synthetic fixtures are predominantly filler and repeated prose.
Reviewing them establishes their limits as fixtures, not a defect in the live
writer. They cannot establish narrative continuity, proper Hebrew agreement,
natural English, vocabulary fit, educational explanation, child agency, stable
character appearance or appropriate emotional pacing. Exact name occurrence is
checked at least once in title/body; meaningful personalization on each page and
pronoun consistency are not guaranteed by that check.

Newborn/infant stories should not be marked defective for lacking conflict or a
conventional plot. Q-03's older-child result is more concerning editorially than
the same repeated-page pattern for an infant. Long books particularly need full
book review rather than spot-checking first/last pages. No output was diagnosed
as developmentally unsuitable from word count alone.

Hebrew alphabet verification here proves literal supplied target/order/base/example
presence against metadata. It does not prove that examples teach correctly, that
final forms are explained as word-final variants, or that unrelated letters do
not appear in words. The approved Roy fixture uses 22 base letters followed by five
final forms; the engine intentionally follows caller order rather than installing
a universal alphabet order in the graph. An arbitrary reordered request being
followed is therefore not a page-order defect.

## Provider error versus invalid output versus quality rejection

New five-case `test_failure_classification_retains_attempt_evidence` reproduces:

| Input at Writer boundary | Final result | Evidence / meaning |
| --- | --- | --- |
| Schema-invalid JSON object | BUDGET_EXCEEDED after 3 calls | Both Writer attempts contain PROVIDER_OUTPUT_INVALID; final code describes exhausted recovery capacity |
| Schema-shaped but out-of-density page | BUDGET_EXCEEDED after 3 calls | Context validation fails before gate; Writer ledger has PROVIDER_OUTPUT_INVALID, not proof of upstream outage |
| Context-valid draft missing supplied name, including rewrite | QUALITY_REJECTED after 3 calls | Quality has PERSONALIZATION_MISSING; final Writer attempt outcome is success because provider/output contract succeeded, while manuscript failed gate |
| Terminal provider refusal | PROVIDER_REFUSED after 2 calls | Plan succeeds; refused Writer is not mislabeled malformed JSON |
| Nonretryable provider availability failure | PROVIDER_UNAVAILABLE after 2 calls | Plan succeeds; unavailable Writer is not an editorial rejection |

All return a failure without `story`; dummy private error text is sanitized.
Other existing tests cover retryable 429/503, input rejection before calls, terminal
unsafe output, malformed/partial recovery, cancellation, deadlines, shared attempts,
unknown usage, token/cost reservations and rewrite page-ID stability.

Operational recommendation: present terminal public code/stop reason separately
from each attempt's safe provider diagnostic. BUDGET_EXCEEDED is not necessarily a
monetary limit; a valid Writer transport/output attempt can precede QUALITY_REJECTED.
Do not retry terminal refusal/safety failures or relabel provider 503 as poor prose.
No new automatic retry, semantic judge, paid evaluation or higher limit is proposed
as an implicit engine fix.

## Previously available safe diagnostic evidence

Read only Agent 1's committed safe summary in AI_GENERATION_RELIABILITY_DESIGN.md
and PROVIDER_DIAGNOSTICS.md at inspected HEAD `49410d0`. This is attributed prior
evidence, not a live run or independent reinspection of its private source artifact:

- Earlier 27-page Hebrew alphabet request: Planner succeeded; both Writer attempts
  received upstream HTTP 503; terminal BUDGET_EXCEEDED with
  attempt_capacity_exhausted; documented HTTP elapsed 10.85 seconds.
- Earlier two-page English bedtime control: two calls succeeded, deterministic gate
  passed, documented elapsed 4.62 seconds. No manuscript was reviewed here.

This supports **provider availability failure** for the documented long run.
It does not demonstrate truncated output, schema rejection, exhausted money, bad
Hebrew, bad teaching, or the causal reason for the service's 503. A short successful
control does not isolate length, language, load, schema complexity or timing.
Earlier QA_HANDOFF remains historical; this newer attributed summary is the
available diagnostic update. The new 42-test diagnostics rerun uses mock HTTP,
not these historical live requests.

## Unverified hypotheses and questions requiring live evaluation

| Question | Status / next safe step |
| --- | --- |
| Long output, Hebrew or educational complexity caused the 503s | Unverified hypothesis; variables were not controlled. No causal claim or new request is justified by this report. |
| Default backoff or sequential chunking would rescue the failed book | Unverified hypothesis. Chunking changes calls, continuity and budget policy; evaluate offline designs first, then seek separate authorization if a live comparison is needed. |
| Gemini consistently produces coherent, age-suitable he/en stories with accurate teaching | Requires separately approved live evaluation plus native-language/educator review of complete manuscripts. Fake acceptance cannot answer it. |
| Character continuity/agency and unnecessary repetition rates on 27-page books | Requires a reviewed evaluation set and full-book human scoring; no frequency estimate is available. |
| Token/output sizing reliably fits live 27/32-page books | Existing arithmetic/admission is heuristic, not provider completion evidence. Preserve limits and unknown usage; evaluate only after separate approval. |

Before any future live evaluation, agree representative age/language/type cases,
native reviewers, editorial rubric/thresholds, privacy handling and explicit fixed
call/cost limits. This report does not authorize such evaluation or any additional
model request. Current work remains offline.

## Verification and handoff actions

Initial new probes: **17 passed, 0 failed, 0 skipped** in 2.00 seconds on Python
3.13.3, Windows, pytest-socket enabled. Passing includes expected bad-quality
acceptance and D-01 reproduction, not resolution.

| Current run | Passed | Failed | Skipped | Scope |
| --- | --- | --- | --- | --- |
| Focused diagnosis/HTTP/v2/quality/development/Gemini adapter regression | 449 | 0 | 0 | 104.65 seconds; includes all 17 new probes |
| Diagnostics snapshot rerun | 42 | 0 | 0 | 66.03 seconds; actual SDK/engine over mocked transports |

These are selected suites, not a new complete-suite run. The earlier full QA run
was 789 cases before these 17 probes were added. Initial 17 and broader 449 overlap;
do not add them as distinct cases. No numerical code-coverage claim.

Broader command (QA root, QA PYTHONPATH as above):

```powershell
& C:/Users/dvir3/OneDrive/Desktop/heroStory/.venv/Scripts/python.exe -m pytest tests/test_qa_engine_diagnosis.py tests/test_qa_v2_http.py tests/test_v2_contracts.py tests/test_v2_execution.py tests/test_quality.py tests/test_development.py tests/test_gemini_provider.py -q
```

Diagnostics snapshot command:

```powershell
$env:PYTHONPATH = 'C:/Users/dvir3/storyforge-qa/qa/.local/diagnostics-snapshot/src'
& C:/Users/dvir3/OneDrive/Desktop/heroStory/.venv/Scripts/python.exe -m pytest qa/.local/diagnostics-snapshot/tests/test_provider_diagnostics.py -q
```

Recommended action order for Agent 1:

1. Reproduce D-01 and fix the local fixture distributor in its owning branch;
   preserve budgets, counts and safe error behavior. Replace characterization
   failure expectation with successful compliant output after the fix.
2. Keep provider outages distinct from invalid outputs and quality failures in
   integration diagnostics; retain all attempts and explicit unknown usage.
3. Agree editorial assurance for Q-01 through Q-05; do not turn all repetition
   or inconclusive language evidence into hard rejection without product approval.
4. Add reviewed language/education data and representative human-review cases;
   distinguish schema correctness from manuscript acceptance in product wording.
5. After integration exists, rerun independent local Fake-only workflows. Request
   separate approval for any live model evaluation; none is performed here.
