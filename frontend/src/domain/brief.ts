import type { Language, StoryRequestV2, StoryType } from "../api/contracts";
import type { Copy } from "../i18n/locales";
export interface BriefDraft {
  name: string;
  age: string;
  ageUnit: "months" | "years";
  language: Language;
  theme: string;
  guidance: string;
  type: StoryType;
  pages: string;
  density: "light" | "standard";
  education: boolean;
  targets: string;
  targetKind: "concept" | "letter";
}
export const initialDraft: BriefDraft = {
  name: "",
  age: "36",
  ageUnit: "months",
  language: "en",
  theme: "",
  guidance: "",
  type: "bedtime",
  pages: "6",
  density: "standard",
  education: false,
  targets: "",
  targetKind: "concept",
};
export type BriefErrors = Partial<
  Record<
    "name" | "age" | "theme" | "guidance" | "pages" | "targets",
    keyof Copy
  >
>;
export function isBriefDraft(value: unknown): value is BriefDraft {
  if (!value || typeof value !== "object") return false;
  const row = value as Record<string, unknown>;
  return (
    Object.entries(initialDraft).every(
      ([key, defaultValue]) =>
        typeof row[key] === typeof defaultValue &&
        (typeof row[key] !== "string" || String(row[key]).length <= 1500),
    ) &&
    ["months", "years"].includes(String(row.ageUnit)) &&
    ["en", "he"].includes(String(row.language)) &&
    ["general", "bedtime", "adventure", "educational", "alphabet"].includes(
      String(row.type),
    ) &&
    ["light", "standard"].includes(String(row.density)) &&
    ["concept", "letter"].includes(String(row.targetKind))
  );
}
export function ageInMonths(
  value: string,
  unit: BriefDraft["ageUnit"],
): number | null {
  if (!/^\d+(?:\.\d+)?$/.test(value)) return null;
  // Decimal arithmetic prevents both binary rounding errors and silently rounded fractional months.
  const [whole, fraction = ""] = value.split(".");
  if (value.length > 100) return null;
  const numerator =
    BigInt(whole + fraction) * BigInt(unit === "years" ? 12 : 1);
  const denominator = 10n ** BigInt(fraction.length);
  if (numerator % denominator !== 0n) return null;
  const months = Number(numerator / denominator);
  return Number.isSafeInteger(months) ? months : null;
}
export function prepareRequest(draft: BriefDraft): {
  request?: StoryRequestV2;
  errors: BriefErrors;
} {
  const errors: BriefErrors = {};
  const age = ageInMonths(draft.age, draft.ageUnit);
  const size = (value: string) => Array.from(value).length;
  const validText = (value: string, max: number) =>
    !!value.trim() &&
    size(value) <= max &&
    !/[\p{Cc}\p{Cs}\p{Cf}]/u.test(value.replace(/[\t\n\r\u200c\u200d]/g, ""));
  if (!validText(draft.name, 40)) errors.name = "invalidName";
  if (age === null) errors.age = "invalidAge";
  if (!validText(draft.theme, 120)) errors.theme = "invalidTheme";
  if (draft.guidance && !validText(draft.guidance, 500))
    errors.guidance = "invalidGuidance";
  const pages = Number(draft.pages);
  if (
    !/^\d+$/.test(draft.pages) ||
    !Number.isInteger(pages) ||
    pages < 1 ||
    pages > 32
  )
    errors.pages = "invalidPages";
  const labels = draft.targets.split(/\r?\n/).map((line) => line.trim());
  const structured = draft.education || draft.type === "alphabet";
  if (
    structured &&
    (labels.length !== pages ||
      labels.some((label) => !validText(label, 40)) ||
      (draft.type === "alphabet" && new Set(labels).size !== labels.length))
  )
    errors.targets = "invalidTargets";
  if (Object.keys(errors).length) return { errors };
  return {
    errors,
    request: {
      schema_version: "2",
      display_name: draft.name,
      age_months: age!,
      language: draft.language,
      theme: draft.theme,
      page_count: pages,
      story_type: draft.type,
      text_density: draft.density,
      ...(draft.guidance ? { guidance: draft.guidance } : {}),
      ...(structured
        ? {
            structure: {
              kind: "ordered_targets",
              targets: labels.map((label, i) => ({
                target_id: `target-${i + 1}`,
                label,
                kind: draft.type === "alphabet" ? "letter" : draft.targetKind,
              })),
            },
          }
        : {}),
    },
  };
}
