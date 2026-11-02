# Implemented validation and quality rules (Milestone 2)

> Approved page-count update: new work uses [explicit-length v2](PAGE_COUNT_V2.md). The user supplies page_count; age controls developmental guidance and page density. Deprecated v1 keeps its original behavior. Historical milestone sections below describe v1 unless labeled v2. No live calls were made in this follow-up; Milestone 7 remains unapproved.

Milestone 2 introduced pure validation and quality functions with no provider calls or graph dependencies. Milestone 3 composes them in a bounded graph without changing these quality policies; see [Orchestration](ORCHESTRATION.md). The five developmental profiles remain unchanged. All values below are configurable product heuristics, not validated developmental standards.

## Interfaces

- `normalize_request(request: StoryRequest, config: DevelopmentConfig, rules: QualityRules = DEFAULT_RULES) -> NormalizedBrief`: pure validation/context resolution. It revalidates the supplied request, checks every nested string for prohibited controls/directives and resolves the age/language profile. It does not trim, normalize, translate, reverse, vocalize or otherwise rewrite supplied text. An immutable brief retains exact names, interests, pronouns, profile and adult/shared read-aloud guidance.
- Invalid or unsupported input raises `NormalizationError` with an existing `GenerationError` (`INPUT_INVALID` or `POLICY_REJECTED`, stage `validation`, non-retryable). Messages contain no rejected values. Raw request parsing remains the caller's responsibility; use the existing strict `StoryRequest` and avoid exposing raw Pydantic errors.
- `assess_story(candidate: Story | str | Mapping[str, object], brief: NormalizedBrief, rules: QualityRules = DEFAULT_RULES) -> QualityReport`: pure assessment of typed stories, raw JSON, or JSON-compatible mappings. Revalidates even typed models, applies configured hard checks and adds advisory observations. Schema errors produce sanitized reports rather than validation exception details.
- Rules are injected explicitly. Default check version is `quality-v1`; default language rubric version is `language-v1`. Normalization captures the rubric version; a mismatch during assessment is terminal. When changing script thresholds, increment the rubric version; increment the check version when changing any assessment rule. Keep the exact immutable rules object with request dependencies in future orchestration.

`Story.validate_for(brief)` remains the Milestone 1 structural contract helper. It does not replace the full assessment function. No new parallel story/report schemas are introduced. `QualityRules` and `ScriptRule` are configuration models using the existing immutable base contract.

## Hard checks and issue codes

| Code | Classification | Meaning |
| --- | --- | --- |
| `STORY_SCHEMA_INVALID` | Repairable | Invalid JSON, required fields/types, direction/language consistency, page ordering/numbering or unique page IDs |
| `LANGUAGE_METADATA_MISMATCH` | Repairable | Story language differs from the brief |
| `PROFILE_MISMATCH` | Repairable | Profile ID or version differs from the captured profile |
| `PAGE_COUNT_MISMATCH` | Repairable | Page count differs from that profile |
| `PAGE_WORD_COUNT` | Repairable; page-specific | Whitespace-delimited page words outside configured hard limits |
| `TOTAL_WORD_COUNT` | Repairable | Total page-text words outside configured hard limits; title excluded |
| `PERSONALIZATION_MISSING` | Repairable | Exact supplied display name absent from title and page text |
| `SCRIPT_MISMATCH` | Repairable | Enough body-letter evidence exists but the configured target-script ratio fails |
| `FORBIDDEN_UNICODE_CONTROL` | Terminal | Prohibited controls in text, IDs or metadata |
| `PROHIBITED_CONTENT` | Terminal | A configured whole-sentence dangerous directive was detected |
| `RUBRIC_VERSION_MISMATCH` | Terminal | Assessment would use a different language rubric from normalization |

Name matching is case-sensitive and exact in code points, with boundaries excluding adjacent letters, marks, digits and underscore. This prevents matching `Ann` inside `Annabelle`. No transliteration, inflection, niqqud stripping or canonical equivalence is applied to personalization. Hebrew prefixes or differently vocalized names do not substitute for one exact occurrence. Preserve the supplied name explicitly at least once. Names may include spaces and punctuation.

Every hard issue blocks acceptance. Any terminal issue forbids automatic repair even if repairable issues also exist. Unsafe decoded text is checked on schema failure as well; malformed JSON that cannot be decoded still fails schema validation. Reports contain only codes, severities, optional page positions, static guidance and non-sensitive counts. They contain no rejected text or name. No logging is performed.

## Unicode policy

Reject Unicode control characters (`Cc`) except tab, LF and CR, lone surrogates (`Cs`), and format characters (`Cf`) except ZWNJ/ZWJ, which permit ordinary joined text and emoji sequences. Explicit bidi embedding/override/isolate controls, directional marks and deprecated directional controls are prohibited. Zero-width space, soft hyphen and embedded BOM are rejected as format controls. Ordinary Hebrew letters, niqqud, punctuation, emoji, newlines and logical Unicode order are preserved.

The directional-control families follow the [Unicode Bidirectional Algorithm specification](https://www.unicode.org/reports/tr9/). General categories and comparison-copy normalization use the standard-library [Unicode database functions](https://docs.python.org/3/library/unicodedata.html). Application direction comes from `rtl`/`ltr` metadata, not embedded controls. These are application input restrictions, not claims that all format controls are intrinsically unsafe.

## Language evidence and acceptance policy

Default rules for each language: at least **20 eligible body letters**, then a minimum **0.80 target-script ratio**. Both values are separately configurable for `he` and `en`. Compare Hebrew-named Unicode letters for Hebrew and Latin-named letters for English; other letters count in the denominator. Marks (including niqqud), digits, punctuation and emoji do not count. Exact name occurrences are excluded. Title text is excluded so a long title cannot mask a body mismatch. No translations are generated.

Below the minimum, including zero eligible letters, emit `LANGUAGE_EVIDENCE_INCONCLUSIVE` as an **advisory**. Do not divide by zero, assert that the language check passed, or reject solely on insufficient evidence. Overall deterministic acceptance is allowed when all hard checks pass, and the report explicitly requests manual language review. This policy applies to every profile, permitting short baby refrains and name/sound-heavy stories. A passing report does not certify the requested language, fluency or safety; names-only or otherwise uninformative text can pass these limited checks and needs human review. An alternative stricter release policy requires a future explicit decision.

Enough letters with an insufficient ratio yields a repairable `SCRIPT_MISMATCH`. This is a coarse script check: Latin letters cannot distinguish English from other Latin-script languages. Repeated sounds are permitted; letter counts are not statistical proof of fluency. Threshold refinement needs bilingual evaluation.

## Narrow prohibited-content policy

Default directive sentences: `drink bleach now`, `you should drink bleach`, `mix bleach and ammonia`, `שתה אקונומיקה עכשיו`, `עליך לשתות אקונומיקה`, and `ערבב אקונומיקה ואמוניה`. Matching compares whole sentences after case folding, decomposition, mark removal and word tokenization on a temporary comparison copy. Stored/returned story text is never transformed.

Sentence boundaries use `. ! ? … ;`, line breaks and Hebrew sof pasuq. `Do not drink bleach` and merely mentioning bleach do not match. The check does not understand context, quotation, obfuscation, negation in general or paraphrases: a quoted complete directive may be rejected, while a longer or modified dangerous instruction may escape detection. Configured matches are terminal, but absence of matches is never proof of safety. No broad moderation coverage, paid moderation service or LLM judge is claimed. Expand rules only with reviewed positive/negative fixtures and a version change.

## Soft observations

All use existing severity `advisory` and never block acceptance:

| Code | Observation |
| --- | --- |
| `SENTENCE_LENGTH_OBSERVATION` | Per-page punctuation-based sentence/utterance counts outside the profile's soft word range; abbreviations and dialogue can distort counts |
| `REPETITION_OBSERVED` | A body token (excluding the name) repeats; repetition can be intentional, especially for babies |
| `REFRAIN_REVIEW` | No repeated body tokens were seen; compare manually with the profile's optional or suggested guidance |
| `VOCABULARY_FORM_COUNT` | Counts of distinct comparison-copy word forms and tokens; not reading difficulty or a vocabulary-age score |
| `VOCABULARY_NARRATIVE_REVIEW` | Explicit manual review of captured vocabulary/narrative guidance; semantic suitability is not measured |
| `READ_ALOUD_REVIEW` | Review adult-read-aloud rhythm; sensory profiles need no conflict or traditional plot |
| `LANGUAGE_EVIDENCE_INCONCLUSIVE` | Insufficient eligible letters; language remains unassessed |

No plot, rhyme, grammar, word-complexity or semantic-coherence requirement is inferred by these heuristics. Newborns/infants retain soothing sequences, repeated sounds and adult-read-aloud guidance. Story creation still does not exist at this milestone.

## Tests and remaining decisions

The default offline suite retains all 115 Milestone 1 tests. New tests cover normalization, all five profiles and exact boundaries in both languages, niqqud, metadata, page/word boundaries, safe reporting, script thresholds, inconclusive evidence, forbidden controls, narrow directive matching and soft/hard classifications. Network sockets remain blocked during test execution; neither module imports a provider.

Open: bilingual threshold calibration and human release policy, reviewed expansion of safety patterns, heuristic sentence segmentation, pronoun presets/grammatical evaluation, older-child profile refinement, and human evaluation criteria. Graph/recovery execution is isolated in Milestone 3's orchestration layer; these functions remain provider-independent. `inspect_output_safety` reuses the same narrow pre-schema checks to produce sanitized terminal issues for adapters without retaining raw malformed responses.
