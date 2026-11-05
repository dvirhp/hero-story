import { test, expect } from "@playwright/test";
import path from "node:path";
import AxeBuilder from "@axe-core/playwright";
test("guest shopping journey: personalized preview, format, cart, discount, decline recovery, simulated order and history", async ({
  page,
}, info) => {
  const calls: string[] = [];
  await page.route("**/*", async (route) => {
    if (
      !route.request().url().startsWith("http://127.0.0.1:5186") ||
      route.request().url().includes("/v3/")
    ) {
      calls.push(route.request().url());
      await route.abort();
    } else await route.continue();
  });
  await page.goto("/");
  await page
    .getByRole("link", { name: "Explore the bookshop" })
    .first()
    .click();
  await page.locator('.book-card-art[href="#/books/sky-whale"]').click();
  await page
    .getByRole("link", { name: /Personalize this book/ })
    .first()
    .click();
  await page.getByLabel("Child’s name", { exact: true }).fill("Maya");
  await page.getByRole("button", { name: "Save to my books" }).click();
  await page.getByRole("button", { name: "Choose format & quantity" }).click();
  await page.getByLabel("Quantity", { exact: true }).fill("2");
  await page.getByRole("button", { name: "Add to bag" }).click();
  await expect(page.locator(".cart-line")).toHaveCount(1);
  await expect(page.locator(".bag-count")).toHaveText("2");
  await page.getByLabel("Quantity", { exact: true }).selectOption("1");
  await page.screenshot({
    path: path.resolve(
      `../docs/frontend-screenshots/cart-premium-${info.project.name}.png`,
    ),
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("link", { name: "Continue as a guest" }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page.getByLabel("First name", { exact: true }).fill("Alex");
  await page.getByLabel("Last name", { exact: true }).fill("Example");
  await page
    .getByLabel("Email address", { exact: true })
    .fill("demo@example.test");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page
    .getByLabel("Street address", { exact: true })
    .fill("123 Sample Street");
  await page.getByLabel("City", { exact: true }).fill("Example City");
  await page.getByLabel("Postal code", { exact: true }).fill("12345");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel(/Express demonstration delivery/).check();
  await page.getByLabel("Promo code", { exact: true }).fill("STORY10");
  await page.getByRole("button", { name: "Apply", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.locator('input[autocomplete="cc-number"]')).toHaveCount(0);
  await page.getByLabel("Preview a declined simulation").check();
  await page
    .getByRole("button", { name: "Simulate order", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "simulation could not finish",
  );
  await page.getByLabel("Preview a declined simulation").uncheck();
  await page.screenshot({
    path: path.resolve(
      `../docs/frontend-screenshots/checkout-premium-${info.project.name}.png`,
    ),
    fullPage: true,
    animations: "disabled",
  });
  const a11y = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(
    a11y.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page
    .getByRole("button", { name: "Simulate order", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "A little magic, ready for its next chapter.",
    }),
  ).toBeVisible();
  await expect(page.locator(".bag-count")).toHaveText("0");
  await expect(
    page.getByText("Simulated · not placed", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: path.resolve(
      `../docs/frontend-screenshots/confirmation-premium-${info.project.name}.png`,
    ),
    fullPage: true,
    animations: "disabled",
  });
  await page
    .getByRole("link", { name: "Your demonstration orders", exact: true })
    .click();
  await page.getByRole("link", { name: "View order", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "The details of your keepsake" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(calls).toEqual([]);
});
