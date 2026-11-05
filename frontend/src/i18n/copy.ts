import { messages } from "./locales";
import { productCopy } from "./product";
import { experience } from "./experience";
import { resolveLocale } from "./registry";
/** Unsupported locale tags fall back before dictionary access; no unsupported-language claim. */
export function copyFor(input: string) {
  const locale = resolveLocale(input);
  return {
    locale,
    core: messages[locale],
    product: productCopy[locale],
    experience: experience[locale],
  };
}
