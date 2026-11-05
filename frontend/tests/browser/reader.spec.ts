import { test, expect } from "@playwright/test";
import path from "node:path";
test("physical book progression follows book language, with paired desktop pages and touch on mobile", async ({
  page,
}, info) => {
  for (const language of ["en", "he"]) {
    await page.goto(`/#/read/sample-moon-fox-${language}`);
    await page
      .getByRole("button", { name: /Open the book/ })
      .first()
      .click();
    const rtl = language === "he";
    await expect(page.locator(".physical-book")).toHaveAttribute(
      "data-book-direction",
      rtl ? "rtl" : "ltr",
    );
    await expect(page.locator('[data-page-number="1"]')).toHaveAttribute(
      "data-physical-side",
      info.project.name === "desktop" ? (rtl ? "left" : "right") : "single",
    );
    await page.keyboard.press(rtl ? "ArrowLeft" : "ArrowRight");
    if (info.project.name === "desktop") {
      await expect(page.locator('[data-page-number="2"]')).toHaveAttribute(
        "data-physical-side",
        rtl ? "right" : "left",
      );
      await expect(page.locator('[data-page-number="3"]')).toHaveAttribute(
        "data-physical-side",
        rtl ? "left" : "right",
      );
    } else {
      await expect(page.locator('[data-page-number="2"]')).toBeVisible();
      await page.locator(".physical-book").evaluate((element, rtl) => {
        const start = new Touch({
          identifier: 0,
          target: element,
          clientX: rtl ? 80 : 280,
          clientY: 200,
        });
        const end = new Touch({
          identifier: 0,
          target: element,
          clientX: rtl ? 280 : 80,
          clientY: 200,
        });
        element.dispatchEvent(
          new TouchEvent("touchstart", { touches: [start], bubbles: true }),
        );
        element.dispatchEvent(
          new TouchEvent("touchend", { changedTouches: [end], bubbles: true }),
        );
      }, rtl);
      await expect(page.locator('[data-page-number="3"]')).toBeVisible();
    }
    await page.getByRole("button", { name: "Page overview" }).click();
    await expect(page.locator(".reader-thumbnails button")).toHaveCount(7);
    await page.screenshot({
      path: path.resolve(
        `../docs/frontend-screenshots/reader-premium-${language}-${info.project.name}.png`,
      ),
      fullPage: true,
      animations: "disabled",
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
});
