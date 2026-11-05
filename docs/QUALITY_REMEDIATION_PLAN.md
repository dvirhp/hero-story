# Quality remediation after independent QA

Status: **assessment/proposal only**, except the separately approved D-01 Fake
fixture fix. No new semantic gate, educational pack, LLM judge, prompt rewrite or
paid evaluation is implemented. Evidence: Agent 4 QA commit `51d5f43`, inspected
read-only at `C:/Users/dvir3/storyforge-qa/docs/AI_ENGINE_QA_REPORT.md` and its
`tests/test_qa_engine_diagnosis.py`. Existing gate policy remains authoritative in
[VALIDATION_AND_QUALITY.md](VALIDATION_AND_QUALITY.md).

## Confirmed defect versus demonstrations

| Evidence | Finding / current disposition |
| --- | --- |
| D-01, P2 fixture defect | Reproduced locally before the fix: an admitted newborn request with a two-word name and 15 entries produced 16 words, including a standalone period. Fixed in `llm/fixtures_v2.py`; regression now requires compliant output and two successful engine attempts |
| Q-01, contradictory character facts | Synthetic he/en witnesses pass current deterministic gate; demonstrated semantic limitation, not proof a live model wrote them |
| Q-02, incorrect supplied Hebrew final-form mapping | Synthetic canonical fixture mutation passes generic schema/metadata checks; linguistic truth is not currently validated |
| Q-03, identical pages | Synthetic copies pass with existing advisory repetition checks, across baby and older ages; advisory policy is deliberate and unchanged |
| Q-04, Latin nonsense | Synthetic nonsense passes script evidence; Latin letters do not establish English fluency |
| Q-05, several sentences in one entry | Entry-count contract is not grammatical sentence counting; no punctuation-only replacement policy introduced |
| Count/order | Agent 4 reproduced no page-count/order regression on exercised paths; this is not a proof of all possible paths |
| Prior live 503s | Recorded upstream failures with unknown root cause; no link established to prose quality, language or length |

Agent 4's 17 original passing characterization probes include intentionally bad
acceptance and the old defect. They are not 17 literary-quality passes, and the
old D-01 expectation must change when integrated. This branch adds regression
tests asserting the correction; it does not modify Agent 4's tests/worktree.

The fix partitions text at replaceable spaces according to actual word gaps,
retains exact multiword names/labels (including multiple spaces), and adds final
punctuation once rather than to every token fragment. It never relaxes the age
density or requested entries. Where a tab-only gap must remain indivisible, it
uses available density headroom; if the minimal fixture strategy cannot satisfy
the combination it returns one explicit nonretryable PROVIDER_OUTPUT_INVALID
Writer failure instead of emitting empty units. This is a documented fixture
capability limit, not a new rejection policy for real writers or proof the request
is mathematically impossible. Synthetic filler is still not children's literature.

## Prioritized work requiring separate approval

| Priority / concern | Correct mechanism | Concrete next deliverable / evaluation |
| --- | --- | --- |
| P1: Hebrew alphabet/final forms | Reviewed declarative educational data plus deterministic pack validation | Versioned Hebrew alphabet pack with 22 base letters and finals ך->כ, ם->מ, ן->נ, ף->פ, ץ->צ; validate declared pack membership/order and base relationships outside graph; review examples and explanations natively |
| P1: explicit target compliance | Existing exact structural checks plus semantic review | Retain one target/page, IDs/order, literal labels, ending-form/example presence; benchmark whether prose teaches that target accurately rather than merely mentioning it |
| P1: natural age-appropriate he/en | Native editorial/semantic evaluation | Bilingual adult read-aloud set across five bands, light/standard density, explicit/absent pronouns, multiword names, dialogue and niqqud; score fluency, agreement, vocabulary, warmth and understandable discovery |
| P1: global narrative coherence | Planning guidance and full-book semantic review | Review goal/discovery, progression, causal links and closure for applicable profiles; baby sensory/refrain books need no conflict or conventional six-beat arc |
| P1: character/setting consistency | Frozen global outline/facts, semantic review | Contrast pairs with contradictions/negation, deliberate transformation, fantasy and time shifts; do not reject legitimate creative change using naive keyword matching |
| P2: unnecessary repetition | Age-aware heuristic warnings and editorial review | Report exact/near-duplicate pages and repeated openings separately from intentional refrains; compare toddler/baby comfort repetition versus older-child formulaic scenes |
| P2: density/readability | Hard existing word/entry checks; soft sentence/vocabulary observations | Keep configured page word ranges and entry counts exact; measure age fit through read-aloud/semantic rubric, not word count alone |

The educational pack needs an explicit reviewed selection/version contract or
server composition policy. Do not silently redefine all generic ordered_targets
as a canonical Hebrew alphabet. Keep user-selected ordering unless a declared
pack promises canonical order. Arbitrary concepts/languages remain generic until
reviewed packs exist. A literal example ending in a final form is not proof it is
a real word, appropriate vocabulary or an accurate explanation. Words on a letter
page naturally contain other letters; never reject them for doing so.

## What can and cannot be strict

Strict deterministic checks: schemas, exact N and numbering, distinct identities,
requested title/target assignments, configured density/entry counts, Unicode
controls, reviewed pack facts when explicitly selected, and narrow existing
unsafe-directive rules. B1 additionally checks canonical representation/bytes and
trusted ownership assertions. None proves emotional engagement or full safety.

Heuristic warnings: duplicate/near-duplicate passages, repeated openings, coarse
sentence length, vocabulary form counts and script evidence. Retain advisory
status until reviewed false-positive cases justify a product policy change.
Insufficient script evidence stays advisory; no dictionary whitelist or blanket
rejection of foreign-looking names, invented words, rhymes or repetition.

Semantic/human review: contradictions, meaningful hero agency, educational
explanation, age fit, pronoun agreement, fluent Hebrew/English, narrative payoff,
creative variety, emotional tone and safety beyond literal directive matches.
Review complete long books, not just sample pages. Human review is necessary for
evaluation/release policy until separately approved automation is measured; no
claim that a passing JSON/gate result is an editorially accepted manuscript.

## Proposed sequence and exit evidence

1. Maintain the corrected Fake regression and existing deterministic baselines.
2. Approve a curated educational-pack contract and bilingual positive/negative
   examples; add pure tests before any provider integration. Include incorrect
   base mappings, invalid examples and legitimate vocabulary/ordering exceptions.
3. Approve human rubric, native reviewers and representative complete manuscripts.
   Score synthetic bad/good contrast cases to validate the rubric itself.
4. Review minimal Planner/Writer guidance changes against that rubric, with
   versioned prompts and unchanged shared accounting. No additional LLM call is
   assumed. Do not introduce a dynamic supervisor or semantic judge implicitly.
5. Only after explicit run/cost approval, evaluate live output and compare rates
   of structural, educational, coherence and fluency failures. Keep provider
   availability separate. Define release thresholds before calling it reliable.

Open decisions: pack selection/versioning, reviewed educational examples and
pronoun forms; human review/release thresholds; any future semantic evaluator's
privacy/call/cost budget; and how product wording distinguishes generated source
checks from edited-Book quality. No such decision is silently implemented here.
