import { test, expect } from "@playwright/test";
import path from "node:path";
test("manual duplicate, illustration position, dedication and consent-based refresh recovery", async ({
  page,
}, info) => {
  await page.goto("/#/studio/new");
  await page.getByLabel("Book title").fill("The very small lighthouse");
  await page
    .getByLabel(/Words on this page/)
    .fill("A light shone across the sea.");
  await page
    .getByRole("button", { name: "Duplicate page", exact: true })
    .click();
  await expect(page.locator(".page-thumbnail")).toHaveCount(2);
  await page.getByLabel("Illustration size", { exact: true }).fill("60");
  await page
    .getByLabel("Illustration horizontal position", { exact: true })
    .fill("25");
  await page.getByText("Cover & dedication", { exact: true }).click();
  await page
    .getByLabel("Cover illustration", { exact: true })
    .selectOption("whale");
  await page
    .getByLabel("Dedication", { exact: true })
    .fill("For every little explorer.");
  await page.getByLabel("Keep my books and bag on refresh in this tab").check();
  await page
    .getByRole("button", { name: "Save draft in this tab", exact: true })
    .click();
  await page.reload();
  await expect(page.getByLabel("Book title")).toHaveValue(
    "The very small lighthouse",
  );
  await expect(page.locator(".page-thumbnail")).toHaveCount(2);
  await page.getByRole("button", { name: "Pages 2", exact: true }).click();
  await expect(
    page.getByLabel("Illustration size", { exact: true }),
  ).toHaveValue("60");
  await page.getByText("Cover & dedication", { exact: true }).click();
  await expect(page.getByLabel("Dedication", { exact: true })).toHaveValue(
    "For every little explorer.",
  );
  await page.screenshot({
    path: path.resolve(
      `../docs/frontend-screenshots/editor-refined-${info.project.name}.png`,
    ),
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("button", { name: /Finish my book/ }).click();
  await expect(
    page.getByRole("heading", { name: "The very small lighthouse" }),
  ).toBeVisible();
  await expect(page.locator(".book-dedication")).toHaveText(
    "For every little explorer.",
  );
  await page
    .getByRole("button", { name: "Choose format & quantity", exact: true })
    .click();
  await page.getByRole("button", { name: "Add to bag", exact: true }).click();
  await page.reload();
  await expect(page.locator(".cart-line")).toHaveCount(1);
  await page
    .getByRole("button", { name: "Clear saved tab progress", exact: true })
    .click();
  expect(
    await page.evaluate(() =>
      Object.keys(sessionStorage).filter((key) =>
        key.startsWith("storyforge.tab."),
      ),
    ),
  ).toEqual([]);
  await page.reload();
  await expect(page.locator(".cart-line")).toHaveCount(0);
});
