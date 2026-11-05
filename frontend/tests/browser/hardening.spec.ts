import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import path from "node:path";
import { experience } from "../../src/i18n/experience";
import { productCopy } from "../../src/i18n/product";
async function accessible(page: import("@playwright/test").Page) {
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(
    result.violations.map((item) => ({
      id: item.id,
      nodes: item.nodes.map((node) => node.target),
    })),
  ).toEqual([]);
}
test("Hebrew guest journey, keyboard personalization and simulated checkout are fully localized", async ({
  page,
}, info) => {
  const e = experience.he,
    p = productCopy.he;
  const unexpected: string[] = [];
  page.on("pageerror", (error) => unexpected.push(error.message));
  await page.route("**/*", async (route) => {
    if (
      !route.request().url().startsWith("http://127.0.0.1:5186") ||
      /\/v[23]\//.test(route.request().url())
    ) {
      unexpected.push(route.request().url());
      await route.abort();
    } else await route.continue();
  });
  await page.goto("/#/personalize/sky-whale");
  await page.getByLabel("Interface language").selectOption("he");
  await page.getByLabel(p.childName, { exact: true }).fill("נועם");
  await page.getByLabel(p.language, { exact: true }).selectOption("he");
  await page.getByRole("button", { name: e.skinDeep, exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("button", { name: e.skinDeep, exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await accessible(page);
  await page.getByRole("button", { name: p.saveLibrary, exact: true }).click();
  await page.getByRole("button", { name: e.configure, exact: true }).click();
  await page.getByRole("button", { name: e.add, exact: true }).click();
  await accessible(page);
  await page.getByRole("link", { name: e.checkout, exact: true }).click();
  await page.getByRole("button", { name: e.next, exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page.getByLabel(e.firstName, { exact: true }).fill("דוגמה");
  await page.getByLabel(e.lastName, { exact: true }).fill("בדיקה");
  await page.getByLabel(e.email, { exact: true }).fill("demo@example.test");
  await page.getByRole("button", { name: e.next, exact: true }).click();
  await page.getByLabel(e.street, { exact: true }).fill("רחוב לדוגמה 1");
  await page.getByLabel(e.city, { exact: true }).fill("עיר לדוגמה");
  await page.getByLabel(e.postcode, { exact: true }).fill("12345");
  await page.getByRole("button", { name: e.next, exact: true }).click();
  await page.getByRole("button", { name: e.next, exact: true }).click();
  await accessible(page);
  await page.screenshot({
    path: path.resolve(
      `../docs/frontend-screenshots/checkout-hebrew-${info.project.name}.png`,
    ),
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("button", { name: e.simulate, exact: true }).click();
  await expect(
    page.getByRole("heading", { name: e.confirmation }),
  ).toBeVisible();
  await accessible(page);
  expect(unexpected).toEqual([]);
  expect(await page.evaluate(() => sessionStorage.length)).toBe(0);
});
test("small phones, tablets and wide screens retain usable RTL/LTR controls without overflow", async ({
  page,
}, info) => {
  test.setTimeout(90000);
  await page.goto("/");
  for (const locale of ["en", "he"] as const) {
    await page.locator("#ui-language").selectOption(locale);
    for (const width of [320, 390, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      for (const route of [
        "/",
        "/books",
        "/books/sky-whale",
        "/personalize/sky-whale",
        "/studio/new",
        "/create/ai",
        "/cart",
        "/checkout",
      ]) {
        await page.evaluate(async (route) => {
          location.hash = route;
          await new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve)),
          );
        }, route);
        await expect(page.locator("main")).toBeVisible();
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
          `${locale} ${width} ${route}`,
        ).toBe(true);
      }
    }
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.evaluate(() => {
    location.hash = "/read/sample-moon-fox-he";
  });
  await page
    .getByRole("button", { name: /פתיחת הספר/ })
    .first()
    .click();
  await expect(page.locator(".physical-book")).toHaveAttribute(
    "data-book-direction",
    "rtl",
  );
  await accessible(page);
  await page.screenshot({
    path: path.resolve(
      `../docs/frontend-screenshots/rtl-wide-${info.project.name}.png`,
    ),
    fullPage: true,
    animations: "disabled",
  });
});
