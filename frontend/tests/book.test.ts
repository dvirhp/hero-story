import { describe, expect, it } from "vitest";
import {
  blankPage,
  bookFromStory,
  canFinalize,
  createBlankBook,
  movePage,
  reindex,
} from "../src/domain/book";
import {
  catalog,
  personalizeTemplate,
  sampleBook,
  templateDefaults,
  templateErrors,
} from "../src/data/catalog";
import { parseRoute } from "../src/routing/router";
import { makeSample } from "../src/api/mock";
import { initialDraft, prepareRequest } from "../src/domain/brief";
describe("canonical frontend books", () => {
  it("preserves educational target assignments when adapting accepted story pages", () => {
    const request = prepareRequest({
      ...initialDraft,
      name: "Alex",
      theme: "Letters",
      pages: "2",
      type: "alphabet",
      targets: "A\nB",
    }).request!;
    const book = bookFromStory(makeSample(request), "Alex");
    expect(book.pages.map((page) => page.targetId)).toEqual([
      "target-1",
      "target-2",
    ]);
  });
  it("uses a versioned common page model across all three methods", () => {
    const manual = createBlankBook("he");
    const template = sampleBook(catalog[0], "en");
    const ai = bookFromStory(
      makeSample(
        prepareRequest({ ...initialDraft, name: "Alex", theme: "Moon" })
          .request!,
      ),
      "Alex",
    );
    expect([manual, template, ai].map((book) => book.method)).toEqual([
      "MANUAL",
      "TEMPLATE_BASED",
      "AI_GENERATED",
    ]);
    for (const book of [manual, template, ai]) {
      expect(book.schemaVersion).toBe("1");
      expect(book.pages[0].pageNumber).toBe(1);
      expect(Array.isArray(book.pages[0].sentenceUnits)).toBe(true);
    }
    expect(ai.pages[0].illustration).toBeNull();
  });
  it("preserves stable IDs and contiguous numbers during reordering", () => {
    const book = createBlankBook("en");
    book.pages.push(blankPage(), blankPage());
    const ids = book.pages.map((page) => page.pageId);
    const moved = movePage(book, 2, 0);
    expect(moved.pages.map((page) => page.pageId)).toEqual([
      ids[2],
      ids[0],
      ids[1],
    ]);
    expect(moved.pages.map((page) => page.pageNumber)).toEqual([1, 2, 3]);
    expect(movePage(book, 0, -1)).toBe(book);
    expect(
      reindex(moved.pages.slice(1)).map((page) => page.pageNumber),
    ).toEqual([1, 2]);
  });
  it("allows incomplete drafts but requires text on every page for finalizing", () => {
    const book = createBlankBook("en");
    expect(canFinalize(book)).toBe(false);
    book.title = "Sky";
    book.pages[0].sentenceUnits = ["Hello"];
    expect(canFinalize(book)).toBe(true);
    book.pages.push(blankPage());
    expect(canFinalize(book)).toBe(false);
  });
});
describe("versioned template fixtures", () => {
  it("does not reinterpret markers embedded in a supplied name", () => {
    const book = personalizeTemplate(
      catalog[0],
      { ...templateDefaults(catalog[0]), name: "{{companion}}" },
      "en",
    );
    expect(book.title).toContain("{{companion}}");
  });
  it("applies outfit choices to both artwork and prose", () => {
    const template = catalog.find((item) => item.id === "small-hero")!;
    const book = personalizeTemplate(
      template,
      { ...templateDefaults(template), name: "Alex", outfit: "striped" },
      "en",
    );
    expect(book.cover).toBe("hero-striped");
    expect(book.pages[0].illustration).toBe("hero-striped");
    expect(book.pages[0].sentenceUnits.join(" ")).toContain("striped sweater");
  });
  it.each(catalog)(
    "validates schema-driven required fields for $id",
    (template) => {
      expect(templateErrors(template, templateDefaults(template)).name).toBe(
        "required",
      );
      const values = { ...templateDefaults(template), name: "נועם" };
      expect(templateErrors(template, values)).toEqual({});
      const book = personalizeTemplate(template, values, "he");
      expect(book.title).toContain("נועם");
      expect(book.template?.version).toBe("demo-1");
      expect(
        book.pages.every(
          (page) => !page.sentenceUnits.some((text) => text.includes("{{")),
        ),
      ).toBe(true);
    },
  );
  it("keeps schemas distinct and validates allowed choices", () => {
    expect(catalog[0].fields.some((field) => field.id === "companion")).toBe(
      true,
    );
    expect(catalog[3].fields.some((field) => field.id === "outfit")).toBe(true);
    expect(catalog[1].fields.some((field) => field.id === "companion")).toBe(
      false,
    );
    expect(
      templateErrors(catalog[0], {
        ...templateDefaults(catalog[0]),
        name: "Alex",
        companion: "unreviewed",
      }).companion,
    ).toBe("required");
  });
  it("includes dedication and chosen companion in real personalized prose", () => {
    const book = personalizeTemplate(
      catalog[0],
      {
        ...templateDefaults(catalog[0]),
        name: "Maya",
        dedication: "For you, always.",
        companion: "rabbit",
      },
      "en",
    );
    expect(book.pages[0].sentenceUnits).toEqual(["For you, always."]);
    expect(book.pages[2].sentenceUnits.join(" ")).toContain("rabbit");
    expect(book.pages.length).toBe(7);
  });
  it("never treats user text as template code or HTML", () => {
    const book = personalizeTemplate(
      catalog[1],
      { ...templateDefaults(catalog[1]), name: "<img src=x>" },
      "en",
    );
    expect(book.title).toContain("<img src=x>");
    expect(
      templateErrors(catalog[1], { name: "x".repeat(41), color: "#b7cfc1" })
        .name,
    ).toBe("tooLong");
  });
});
describe("explicit routes", () => {
  it.each([
    ["#/", "home"],
    ["#/books?age=babies", "discover"],
    ["#/create/ai", "create"],
    ["#/studio/new", "editor"],
    ["#/books/sky-whale", "product"],
    ["#/personalize/moon-fox", "personalize"],
    ["#/read/demo-moon", "reader"],
    ["#/my-books", "library"],
    ["#/unknown", "not-found"],
  ])("routes %s to %s", (hash, page) =>
    expect(parseRoute(hash).page).toBe(page),
  );
  it("rejects malformed paths instead of using them as IDs", () =>
    expect(parseRoute("#/read/<script>").page).toBe("not-found"));
});
