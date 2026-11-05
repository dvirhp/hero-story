/** UI locales are registered separately from server-supported story languages. */
export const uiLocales = {
  en: { label: "English", direction: "ltr", locale: "en" },
  he: { label: "עברית", direction: "rtl", locale: "he" },
} as const;
export type UiLocale = keyof typeof uiLocales;
export const fallbackLocale: UiLocale = "en";
export function resolveLocale(input: string): UiLocale {
  const candidate = input.trim().toLowerCase().replaceAll("_", "-");
  for (const key of [candidate, candidate.split("-")[0]]) {
    if (Object.hasOwn(uiLocales, key)) return key as UiLocale;
  }
  return fallbackLocale;
}
export function readingDirection(bookLanguage: string): "ltr" | "rtl" {
  return uiLocales[resolveLocale(bookLanguage)].direction;
}
