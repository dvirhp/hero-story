/** Wire contract inspected at backend commit 5ae24e9. No provider selection in HTTP input. */
export type Language = "en" | "he";
export type StoryType =
  | "general"
  | "bedtime"
  | "adventure"
  | "educational"
  | "alphabet";
export interface EducationalTarget {
  target_id: string;
  label: string;
  kind: "concept" | "letter";
  base_form?: string | null;
  example_word?: string | null;
}
export interface OrderedTargets {
  kind: "ordered_targets";
  targets: EducationalTarget[];
  sentence_units_per_page?: { minimum: number; maximum: number } | null;
}
export type NarrativePronouns =
  | {
      language: "en";
      subject: string;
      object: string;
      possessive_determiner: string;
      possessive_pronoun: string;
      reflexive: string;
      verb_agreement: "singular" | "plural";
    }
  | {
      language: "he";
      subject: string;
      object: string;
      possessive: string;
      grammatical_agreement: "masculine_singular" | "feminine_singular";
    };
export interface StoryRequestV2 {
  schema_version: "2";
  display_name: string;
  age_months: number;
  language: Language;
  theme: string;
  page_count: number;
  story_type: StoryType;
  text_density: "light" | "standard";
  guidance?: string | null;
  interests?: string[];
  narrative_pronouns?: NarrativePronouns | null;
  structure?: OrderedTargets | null;
  requested_title?: string | null;
}
export interface StoryPage {
  page_id: string;
  page_number: number;
  target_id: string | null;
  sentence_units: string[];
}
export interface StoryV2 {
  schema_version: "2";
  title: string;
  language: Language;
  direction: "ltr" | "rtl";
  profile_id: string;
  profile_version: string;
  page_count: number;
  pages: StoryPage[];
}
export interface QualityReport {
  passed: boolean;
  check_version: string;
  rubric_version: string;
  issues: {
    code: string;
    severity: "repairable" | "terminal" | "advisory";
    page_number: number | null;
    guidance: string;
  }[];
}
export interface GenerationError {
  code:
    | "INPUT_INVALID"
    | "POLICY_REJECTED"
    | "PROVIDER_OUTPUT_INVALID"
    | "PROVIDER_UNAVAILABLE"
    | "PROVIDER_REFUSED"
    | "CONFIGURATION_ERROR"
    | "DEADLINE_EXCEEDED"
    | "CANCELLED"
    | "BUDGET_EXCEEDED"
    | "QUALITY_REJECTED";
  stage: "validation" | "planner" | "writer" | "quality";
  retryable: boolean;
  message: string;
}
interface TokenUsage {
  source: "reported" | "estimated" | "unknown";
  input_tokens: number | null;
  output_tokens: number | null;
  cached_input_tokens: number | null;
  reasoning_output_tokens: number | null;
}
interface AttemptRecord {
  stage: "planner" | "writer";
  attempt_number: number;
  provider: string;
  model: string;
  prompt_version: string;
  latency_seconds: number;
  usage: TokenUsage;
  estimated_cost_usd: number | null;
  reserved_cost_usd: number;
  pricing_version: string | null;
  outcome: "success" | "failure";
  error: GenerationError | null;
}
interface ResultBase {
  request_id: string;
  total_latency_seconds: number;
  usage: {
    attempts: AttemptRecord[];
    known_estimated_cost_usd: number;
    upper_estimated_cost_usd: number;
    has_unknown_usage: boolean;
    has_unknown_cost: boolean;
  };
}
export interface GenerationSuccessV2 extends ResultBase {
  status: "success";
  story: StoryV2;
  quality: QualityReport;
  resolved_constraints: {
    page_count: number;
    words_per_page: { minimum: number; maximum: number };
    total_words: { minimum: number; maximum: number };
    target_ids: string[];
    sentence_units_per_page: { minimum: number; maximum: number } | null;
    policy_version: string;
  };
}
export interface GenerationFailure extends ResultBase {
  status: "failure";
  error: GenerationError;
  quality: QualityReport | null;
}
export type GenerationResultV2 = GenerationSuccessV2 | GenerationFailure;
/** UI needs approved story data only; HTTP accounting stays at the transport boundary. */
export interface StoryService {
  generate(request: StoryRequestV2, signal: AbortSignal): Promise<StoryV2>;
}
