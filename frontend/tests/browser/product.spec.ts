import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import path from "node:path";
const screenshots = path.resolve("../docs/frontend-screenshots");
const forbidden = new WeakMap<Page, string[]>();
const exceptions = new WeakMap<Page, string[]>();
test.beforeEach(async ({ page }) => {
  forbidden.set(page, []);
  exceptions.set(page, []);
  page.on("pageerror", (error) => exceptions.get(page)!.push(error.message));
  await page.route("**/*", async (route) => {
    const url = route.request().url();
    if (!url.startsWith("http://127.0.0.1:5186") || url.includes("/v2/")) {
      forbidden.get(page)!.push(url);
      await route.abort();
    } else await route.continue();
  });
});
test.afterEach(async ({ page }) => {
  expect(exceptions.get(page)).toEqual([]);
  expect(forbidden.get(page)).toEqual([]);
});
async function shot(page: Page, name: string) {
  await page.screenshot({
    path: path.join(screenshots, `${name}.png`),
    fullPage: true,
    animations: "disabled",
  });
}
async function noOverflow(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
}
async function accessible(page: Page) {
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(
    result.violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
}
async function aiReview(page: Page) {
  await page.getByLabel("Child’s name", { exact: true }).fill("Alex");
  await page.getByLabel("Age", { exact: true }).fill("0");
  await page.getByLabel("Age unit").selectOption("months");
  await page.getByRole("button", { name: "Continue", exact: false }).click();
  await page
    .getByLabel("What is the story about?")
    .fill("A moonlit alphabet garden");
  await page.getByLabel("Story type").selectOption("alphabet");
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByLabel("Number of pages").fill("3");
  await page.getByLabel("Learning targets", { exact: true }).fill("A\nB\nC");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(
    page.getByRole("heading", { name: "A little look before the magic." }),
  ).toBeVisible();
}
test("bookshop, discovery, product previews and responsive navigation", async ({
  page,
}, info) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "How will your story begin?" }),
  ).toBeVisible();
  await shot(page, `home-${info.project.name}`);
  await noOverflow(page);
  await accessible(page);
  await page
    .getByRole("link", { name: "Explore the bookshop" })
    .first()
    .click();
  await page.getByRole("button", { name: "Bedtime", exact: true }).click();
  await expect(page.locator(".book-card")).toHaveCount(1);
  await page.getByLabel("Find a story").fill("not a book");
  await expect(
    page.getByRole("heading", { name: "No books in this little corner yet." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Show all stories" }).click();
  await expect(page.locator(".book-card")).toHaveCount(6);
  await shot(page, `catalog-${info.project.name}`);
  await noOverflow(page);
  await accessible(page);
  await page.locator('.book-card-art[href="#/books/sky-whale"]').click();
  await expect(
    page.getByRole("heading", { name: "The Sky-Whale Express" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();
  await noOverflow(page);
  await accessible(page);
  await shot(page, `product-${info.project.name}`);
  await page.goBack();
  await expect(page.locator(".book-card")).toHaveCount(6);
  if (info.project.name === "mobile") {
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    await expect(page.getByRole("navigation", { name: "Menu" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(
      page.getByRole("button", { name: "Menu", exact: true }),
    ).toBeFocused();
  }
});
test("AI wizard reviews exact newborn age and count, cancels, reads and saves sample", async ({
  page,
}, info) => {
  await page.goto("/#/create/ai");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByLabel("Child’s name", { exact: true })).toBeFocused();
  await aiReview(page);
  await expect(page.locator("dd").filter({ hasText: /^0$/ })).toBeVisible();
  await shot(page, `ai-review-${info.project.name}`);
  await accessible(page);
  await noOverflow(page);
  await page.getByRole("button", { name: "Make our sample story" }).click();
  await expect(
    page.getByRole("heading", { name: "A little world is on its way…" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByLabel("Child’s name", { exact: true })).toHaveValue(
    "Alex",
  );
  await aiReview(page);
  await page.getByRole("button", { name: "Make our sample story" }).click();
  await expect(
    page.getByRole("heading", { name: "The seed that held the moonlight" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Save to my books", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Saved in this tab" }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: /Open the book/ })
    .first()
    .click();
  await expect(page.getByRole("status")).toHaveText("Page 1 of 3");
  await page.getByRole("button", { name: "Next page" }).click();
  if(info.project.name==='mobile') await page.getByRole("button", { name: "Next page" }).click();
  await expect(page.getByRole("button", { name: "Next page" })).toBeDisabled();
  await noOverflow(page);
  await accessible(page);
  await shot(page, `ai-reader-${info.project.name}`);
});
test("template schema, companion preview, save and reopen without AI", async ({
  page,
}, info) => {
  await page.goto("/#/personalize/sky-whale");
  await page.getByRole("button", { name: "Save to my books" }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page.getByLabel("Child’s name", { exact: true }).fill("Maya");
  await page.getByLabel("A traveling companion").selectOption("rabbit");
  await page
    .getByLabel("A little dedication")
    .fill("For your big little dreams.");
  await page.getByRole("button", { name: "Peek inside" }).click();
  await expect(page.locator(".personal-preview")).toContainText(
    "For your big little dreams.",
  );
  await noOverflow(page);
  await accessible(page);
  await shot(page, `personalize-${info.project.name}`);
  await page.getByRole("button", { name: "Save to my books" }).click();
  await expect(
    page.getByRole("heading", { name: "Maya & the Sky-Whale Express" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /Open the book/ })
    .first()
    .click();
  await expect(page.getByRole("article")).toContainText(
    "For your big little dreams.",
  );
  await page.getByRole("button", { name: "Next page" }).click();
  if(info.project.name==='mobile') await page.getByRole("button", { name: "Next page" }).click();
  await expect(page.getByRole("article")).toContainText("rabbit");
  await page.getByRole("link", { name: "Back to my books" }).click();
  await expect(
    page.getByRole("heading", { name: "Maya & the Sky-Whale Express" }),
  ).toBeVisible();
  await shot(page, `library-${info.project.name}`);
  await accessible(page);
});
test("manual studio edits, reorders, removes, saves, reopens, previews and finalizes", async ({
  page,
}, info) => {
  await page.goto("/#/studio/new");
  await page.getByRole("button", { name: /Finish my book/ }).click();
  await expect(page.getByRole("status")).toContainText("Add a title");
  await page.getByLabel("Book title").fill("Maya and the cloud");
  await page
    .getByLabel(/Words on this page/)
    .fill("A little cloud came to visit.");
  await page.getByRole("button", { name: /Add a page/ }).click();
  await page
    .getByLabel(/Words on this page/)
    .fill("Together, they watched the stars.");
  await page.getByLabel("Page layout").selectOption("full");
  await page.getByLabel("Page color").selectOption("lavender");
  await page.getByRole("button", { name: "Moon", exact: true }).click();
  await page.getByRole("button", { name: "Move earlier" }).click();
  await expect(page.getByLabel(/Words on this page/)).toHaveValue(
    "Together, they watched the stars.",
  );
  await page.getByRole("button", { name: /Add a page/ }).click();
  await page.getByRole("button", { name: "Remove page", exact: true }).click();
  await expect(page.locator(".page-thumbnail")).toHaveCount(2);
  await noOverflow(page);
  await accessible(page);
  await shot(page, `studio-${info.project.name}`);
  await page.getByRole("button", { name: "Save draft in this tab" }).click();
  await page
    .getByRole("link", { name: "My books", exact: true })
    .first()
    .click();
  await page
    .locator("article")
    .filter({ has: page.getByRole("heading", { name: "Maya and the cloud" }) })
    .getByRole("link", { name: "Continue editing", exact: true })
    .click();
  await expect(page.getByLabel("Book title")).toHaveValue("Maya and the cloud");
  await page.getByRole("button", { name: "Preview book" }).click();
  await expect(
    page.getByRole("heading", { name: "Maya and the cloud" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /Open the book/ })
    .first()
    .click();
  await expect(page.getByRole("article")).toContainText(
    "Together, they watched the stars.",
  );
  await noOverflow(page);
  await shot(page, `manual-reader-${info.project.name}`);
  await page
    .getByRole("link", { name: "Continue editing", exact: true })
    .click();
  await page.getByRole("button", { name: /Finish my book/ }).click();
  await expect(
    page.getByRole("heading", { name: "Maya and the cloud" }),
  ).toBeVisible();
});
test("Hebrew template and manual journeys maintain RTL, keyboard reading and mixed language", async ({
  page,
}, info) => {
  await page.goto("/#/personalize/moon-fox");
  await page.getByLabel("Interface language").selectOption("he");
  await page.getByLabel("שפת הספר", { exact: true }).selectOption("he");
  await page.getByLabel("שם הילד או הילדה", { exact: true }).fill("נועם");
  await page.getByRole("button", { name: "שמירה בספרים שלי" }).click();
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await page
    .getByRole("button", { name: /פתיחת הספר/ })
    .first()
    .click();
  await expect(page.getByRole("article")).toHaveAttribute("dir", "rtl");
  await page.keyboard.press("ArrowLeft");
  await expect(page.getByRole("status")).toHaveText(info.project.name==='desktop'?"עמוד 2–3 מתוך 6":"עמוד 2 מתוך 6");
  await noOverflow(page);
  await accessible(page);
  await shot(page, `hebrew-reader-${info.project.name}`);
  await page.getByLabel("שפת הממשק").selectOption("en");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await expect(page.getByRole("article")).toHaveAttribute("dir", "rtl");
  await page
    .getByRole("link", { name: "Create Your Own", exact: true })
    .first()
    .click();
  await page.getByLabel("Book title").fill("הענן של נועם");
  await page.getByLabel("Book language", { exact: true }).selectOption("he");
  await page.getByLabel(/Words on this page/).fill("ענן קטן חיכה ליד החלון.");
  await expect(page.getByLabel(/Words on this page/)).toHaveAttribute(
    "dir",
    "rtl",
  );
  await page.getByRole("button", { name: /Finish my book/ }).click();
  await page
    .getByRole("button", { name: /Open the book/ })
    .first()
    .click();
  await expect(page.getByRole("article")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("article")).toContainText("ענן קטן");
  await page.getByRole("link", { name: "Create with AI", exact: true }).click();
  await page.getByLabel("Interface language").selectOption("he");
  await page.getByLabel("שם הילד או הילדה", { exact: true }).fill("נועם");
  await page.getByLabel("גיל", { exact: true }).fill("0");
  await page.getByLabel("שפת הסיפור", { exact: true }).selectOption("he");
  await page.getByRole("button", { name: "ממשיכים" }).click();
  await page.getByLabel("על מה הסיפור?").fill("גינה שקטה");
  await page.getByRole("button", { name: "ממשיכים" }).click();
  await page.getByLabel("מספר עמודים").fill("1");
  await page.getByRole("button", { name: "ממשיכים" }).click();
  await page.getByRole("button", { name: "יצירת הסיפור לדוגמה" }).click();
  await expect(
    page.getByRole("heading", { name: "הזרע ששמר אור ירח" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /פתיחת הספר/ })
    .first()
    .click();
  await expect(page.getByRole("article")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("status")).toHaveText("עמוד 1 מתוך 1");
  await noOverflow(page);
});
test("responsive route sweep, keyboard skip, error, empty and help states", async ({
  page,
}, info) => {
  const originalViewport = page.viewportSize()!;
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
  for (const route of [
    "/",
    "/books",
    "/books/moon-fox",
    "/personalize/small-hero",
    "/create/ai",
    "/my-books",
    "/about",
    "/help",
    "/privacy",
    "/read/missing",
    "/generation-error",
    "/does-not-exist",
  ]) {
    await page.goto(`/#${route}`);
    await expect(page.locator("main")).toBeVisible();
    await noOverflow(page);
    await expect(page.locator("h1")).toHaveCount(1);
  }
  await expect(
    page.getByRole("heading", { name: "This page wandered off into a story." }),
  ).toBeVisible();
  await page.goto("/#/generation-error");
  await expect(page.getByRole("alert")).toBeVisible();
  await accessible(page);
  await page.getByRole("button", { name: "Return to my brief" }).click();
  await expect(page.getByLabel("Child’s name", { exact: true })).toBeVisible();
  for (const width of [320, 768, 1024]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await noOverflow(page);
    await page.goto("/#/studio/new");
    await expect(page.getByLabel("Book title")).toBeVisible();
    await noOverflow(page);
  }
  await page.setViewportSize(originalViewport);
  await page.goto("/#/help");
  await page.getByText("Where are my books saved?", { exact: true }).click();
  await expect(page.getByText(/Only in this tab/)).toBeVisible();
  await shot(page, `help-${info.project.name}`);
});
