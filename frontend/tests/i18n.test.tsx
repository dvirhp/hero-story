import { expect, it } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { copyFor } from "../src/i18n/copy";
import {
  uiLocales,
  resolveLocale,
  readingDirection,
} from "../src/i18n/registry";
import { QuotaPanel } from "../src/components/QuotaPanel";
import type { DailyUsage } from "../src/api/productPorts";
it("resolves regional tags, falls back for unsupported locales, and has every reviewed dictionary key", () => {
  expect(resolveLocale("he-IL")).toBe("he");
  expect(resolveLocale("EN_us")).toBe("en");
  expect(resolveLocale("fr-FR")).toBe("en");
  expect(readingDirection("he-IL")).toBe("rtl");
  const base = copyFor("en");
  for (const locale of Object.keys(uiLocales)) {
    const translated = copyFor(locale);
    for (const group of ["core", "product", "experience"] as const) {
      expect(Object.keys(translated[group]).sort()).toEqual(
        Object.keys(base[group]).sort(),
      );
      expect(
        Object.values(translated[group]).every(
          (value) => typeof value === "string" && value.length > 0,
        ),
      ).toBe(true);
    }
  }
  expect(copyFor("unknown").product).toBe(base.product);
});
it("does not invent a remaining allowance; story and image balances are independent server inputs", () => {
  const view = render(<QuotaPanel locale="en" />);
  expect(screen.getByText("Server allowance not connected")).toBeDefined();
  const usage: DailyUsage = {
    policy_version: "proposal",
    timezone: "UTC",
    day: "2026-11-05",
    reset_at: "2026-11-06T00:00:00Z",
    capabilities: {
      story_generation: { limit: 10, consumed: 8, reserved: 1, remaining: 1 },
      image_generation: { limit: 10, consumed: 0, reserved: 0, remaining: 10 },
    },
  };
  view.rerender(<QuotaPanel locale="en" usage={usage} />);
  expect(screen.getByText("1 / 10")).toBeDefined();
  expect(screen.getByText("10 / 10")).toBeDefined();
  cleanup();
});
