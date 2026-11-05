import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../src/App";
import { makeSample } from "../src/api/mock";
import type { StoryService } from "../src/api/contracts";
afterEach(cleanup);
beforeEach(() => {
  window.history.replaceState(null, "", "#/");
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
});
function renderAt(path: string, service?: StoryService) {
  window.history.replaceState(null, "", `#${path}`);
  return render(<App service={service} />);
}
async function fillAi() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Child’s name"), "Alex");
  await user.click(screen.getByRole("button", { name: /Continue/ }));
  await user.type(
    screen.getByLabelText("What is the story about?"),
    "Moon garden",
  );
  await user.click(screen.getByRole("button", { name: /Continue/ }));
  await user.click(screen.getByRole("button", { name: /Continue/ }));
  return user;
}
describe("full product journeys", () => {
  it("closes the mobile menu with Escape even while focus remains on its toggle", async () => {
    render(<App />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Menu" }));
    expect(screen.getByRole("navigation", { name: "Menu" })).toBeDefined();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("navigation", { name: "Menu" })).toBeNull();
    expect(document.activeElement).toBe(
      screen.getByRole("button", { name: "Menu" }),
    );
  });
  it("exposes all three confirmed methods on the homepage", () => {
    render(<App />);
    expect(
      screen.getByRole("heading", { name: "Create with AI" }),
    ).toBeDefined();
    expect(
      screen.getByRole("heading", { name: "Personalize a Book" }),
    ).toBeDefined();
    expect(
      screen.getByRole("heading", { name: "Create Your Own" }),
    ).toBeDefined();
  });
  it("reviews before generation, reads pages and explicitly saves an AI sample", async () => {
    const generate = vi
      .fn<StoryService["generate"]>()
      .mockImplementation(async (request) => makeSample(request));
    renderAt("/create/ai", { generate });
    const user = await fillAi();
    expect(generate).not.toHaveBeenCalled();
    expect(screen.getByText("36", { selector: "dd" })).toBeDefined();
    await user.click(
      screen.getByRole("button", { name: /Make our sample story/ }),
    );
    await screen.findByRole("heading", {
      name: "The seed that held the moonlight",
    });
    expect(generate).toHaveBeenCalledTimes(1);
    expect(generate.mock.calls[0][0].page_count).toBe(6);
    await user.click(
      screen.getAllByRole("button", { name: /Open the book/ })[0],
    );
    expect(screen.getByRole("status").textContent).toBe("Page 1 of 6");
    for (let i = 0; i < 5; i++)
      await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(
      (screen.getByRole("button", { name: "Next page" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    await user.click(screen.getByRole("button", { name: "Save to my books" }));
    expect(
      (
        screen.getByRole("button", {
          name: "Saved in this tab",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
  });
  it("validates the current wizard step and focuses the invalid field", async () => {
    const generate = vi.fn();
    renderAt("/create/ai", { generate });
    fireEvent.click(screen.getByRole("button", { name: /Continue/ }));
    expect(screen.getByRole("alert").textContent).toContain("highlighted");
    expect(generate).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(document.activeElement).toBe(
        screen.getByLabelText("Child’s name"),
      ),
    );
  });
  it("cancels a pending request and ignores late completion", async () => {
    let resolve!: (story: ReturnType<typeof makeSample>) => void;
    const generate = vi
      .fn<StoryService["generate"]>()
      .mockImplementation(() => new Promise((done) => (resolve = done)));
    renderAt("/create/ai", { generate });
    const user = await fillAi();
    await user.click(
      screen.getByRole("button", { name: /Make our sample story/ }),
    );
    await screen.findByRole("heading", {
      name: "A little world is on its way…",
    });
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await screen.findByLabelText("Child’s name");
    expect(generate.mock.calls[0][1].aborted).toBe(true);
    resolve(makeSample(generate.mock.calls[0][0]));
    await waitFor(() =>
      expect(screen.getByLabelText("Child’s name")).toBeDefined(),
    );
    expect(screen.queryByRole("article")).toBeNull();
  });
  it("keeps the brief after a service failure and hides diagnostics", async () => {
    renderAt("/create/ai", {
      generate: vi.fn().mockRejectedValue(new Error("private diagnostic")),
    });
    const user = await fillAi();
    await user.click(
      screen.getByRole("button", { name: /Make our sample story/ }),
    );
    await screen.findByRole("alert");
    expect(screen.queryByText("private diagnostic")).toBeNull();
    await user.click(
      screen.getByRole("button", { name: "Return to my brief" }),
    );
    expect(
      ((await screen.findByLabelText("Child’s name")) as HTMLInputElement)
        .value,
    ).toBe("Alex");
  });
  it("filters catalog and recovers from empty search", async () => {
    renderAt("/books");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Bedtime" }));
    expect(screen.getAllByRole("article").length).toBe(1);
    await user.type(screen.getByLabelText("Find a story"), "zzzz");
    expect(
      screen.getByRole("heading", {
        name: "No books in this little corner yet.",
      }),
    ).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Show all stories" }));
    expect(screen.getAllByRole("article").length).toBe(6);
  });
  it("renders per-template fields, previews changes and saves without AI", async () => {
    const generate = vi.fn();
    renderAt("/personalize/sky-whale", { generate });
    const user = userEvent.setup();
    expect(screen.getByLabelText(/A traveling companion/)).toBeDefined();
    expect(screen.queryByLabelText(/Explorer’s outfit/)).toBeNull();
    await user.type(screen.getByLabelText(/Child’s name/), "Maya");
    await user.selectOptions(
      screen.getByLabelText(/A traveling companion/),
      "rabbit",
    );
    expect(screen.getByText("Maya & the Sky-Whale Express")).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Save to my books" }));
    await screen.findByRole("heading", {
      name: "Maya & the Sky-Whale Express",
    });
    expect(generate).not.toHaveBeenCalled();
  });
  it("validates template required fields before saving", async () => {
    renderAt("/personalize/moon-fox");
    fireEvent.click(screen.getByRole("button", { name: "Save to my books" }));
    expect(screen.getByRole("alert").textContent).toContain("marked");
    expect(screen.getByText("Please add this detail.")).toBeDefined();
  });
  it("edits, reorders, previews, saves and reopens a manual draft", async () => {
    const generate = vi.fn();
    renderAt("/studio/new", { generate });
    const user = userEvent.setup();
    await screen.findByLabelText("Book title");
    await user.type(screen.getByLabelText("Book title"), "My sky book");
    await user.type(screen.getByLabelText(/Words on this page/), "First page");
    await user.click(screen.getByRole("button", { name: /Add a page/ }));
    await user.type(screen.getByLabelText(/Words on this page/), "Second page");
    await user.click(screen.getByRole("button", { name: "Move earlier" }));
    expect(
      (screen.getByLabelText(/Words on this page/) as HTMLTextAreaElement)
        .value,
    ).toBe("Second page");
    await user.click(
      screen.getByRole("button", { name: "Save draft in this tab" }),
    );
    expect(screen.getByRole("status").textContent).toContain("Draft saved");
    await user.click(screen.getByRole("button", { name: "Preview book" }));
    await screen.findByRole("heading", { name: "My sky book" });
    await user.click(screen.getByRole("link", { name: "Continue editing" }));
    await screen.findByLabelText("Book title");
    expect(
      (screen.getByLabelText("Book title") as HTMLInputElement).value,
    ).toBe("My sky book");
    await user.click(screen.getByRole("button", { name: /Finish my book/ }));
    await screen.findByRole("heading", { name: "My sky book" });
    expect(generate).not.toHaveBeenCalled();
  });
  it("duplicates a page in place and keeps reordering reversible", async () => {
    renderAt("/studio/new");
    const user = userEvent.setup();
    await screen.findByLabelText("Book title");
    await user.type(screen.getByLabelText(/Words on this page/), "Original page");
    await user.click(screen.getByRole("button", { name: "Duplicate page" }));
    expect(
      screen.getAllByRole("button", { name: /^Pages \d+$/ }),
    ).toHaveLength(2);
    expect(
      (screen.getByLabelText(/Words on this page/) as HTMLTextAreaElement).value,
    ).toBe("Original page");
    await user.click(screen.getByRole("button", { name: "Pages 1" }));
    expect(
      (screen.getByLabelText(/Words on this page/) as HTMLTextAreaElement).value,
    ).toBe("Original page");
    await user.click(screen.getByRole("button", { name: "Pages 2" }));
    const text = screen.getByLabelText(/Words on this page/) as HTMLTextAreaElement;
    await user.clear(text);
    await user.type(text, "Copied page");
    await user.click(screen.getByRole("button", { name: "Move earlier" }));
    expect(
      (screen.getByLabelText(/Words on this page/) as HTMLTextAreaElement).value,
    ).toBe("Copied page");
    await user.click(screen.getByRole("button", { name: "Pages 2" }));
    expect(
      (screen.getByLabelText(/Words on this page/) as HTMLTextAreaElement).value,
    ).toBe("Original page");
  });
  it("keeps the unsaved warning through preview navigation", async () => {
    renderAt("/studio/new");
    const user = userEvent.setup();
    await screen.findByLabelText("Book title");
    expect(screen.getByRole("status").textContent).toContain(
      "No unsaved changes.",
    );
    await user.type(screen.getByLabelText("Book title"), "Preview warning");
    expect(screen.getByRole("status").textContent).toContain(
      "Changes have not been saved",
    );
    await user.click(screen.getByRole("button", { name: "Preview book" }));
    await screen.findByRole("heading", { name: "Preview warning" });
    await user.click(screen.getByRole("link", { name: "Continue editing" }));
    await screen.findByLabelText("Book title");
    expect(screen.getByRole("status").textContent).toContain(
      "Changes have not been saved",
    );
    await user.click(
      screen.getByRole("button", { name: "Save draft in this tab" }),
    );
    expect(screen.getByRole("status").textContent).toContain("Draft saved");
    await user.click(screen.getByRole("button", { name: "Preview book" }));
    await screen.findByRole("heading", { name: "Preview warning" });
    await user.click(screen.getByRole("link", { name: "Continue editing" }));
    await screen.findByLabelText("Book title");
    expect(screen.getByRole("status").textContent).toContain(
      "No unsaved changes.",
    );
  });
  it("edits a copy of an AI sample without mutating the saved original", async () => {
    const generate = vi
      .fn<StoryService["generate"]>()
      .mockImplementation(async (request) => makeSample(request));
    renderAt("/create/ai", { generate });
    const user = await fillAi();
    await user.click(
      screen.getByRole("button", { name: /Make our sample story/ }),
    );
    await screen.findByRole("heading", {
      name: "The seed that held the moonlight",
    });
    await user.click(screen.getByRole("button", { name: "Save to my books" }));
    await user.click(screen.getByRole("button", { name: "Edit a copy" }));
    await screen.findByLabelText("Book title");
    expect(
      (screen.getByLabelText("Book title") as HTMLInputElement).value,
    ).toBe("The seed that held the moonlight");
    expect(screen.getByText(/An edited copy is your own draft/)).toBeDefined();
    const title = screen.getByLabelText("Book title");
    await user.clear(title);
    await user.type(title, "Our edited copy");
    await user.click(
      screen.getByRole("button", { name: "Save draft in this tab" }),
    );
    await user.click(screen.getAllByRole("link", { name: "My books" })[0]!);
    expect(
      screen.getByRole("heading", { name: "Our edited copy" }),
    ).toBeDefined();
    const original = screen
      .getAllByRole("article")
      .find((article) =>
        within(article).queryByRole("heading", {
          name: "The seed that held the moonlight",
        }),
      );
    expect(original).toBeDefined();
    await user.click(within(original!).getByRole("link", { name: /Open book/ }));
    expect(
      screen.getByRole("heading", { name: "The seed that held the moonlight" }),
    ).toBeDefined();
    await user.click(
      screen.getAllByRole("button", { name: /Open the book/ })[0]!,
    );
    expect(screen.getByRole("article").textContent).toContain(
      "Alex found a small golden seed beside the window.",
    );
  });
  it("prevents finalizing a blank manual book and removing its only page", async () => {
    renderAt("/studio/new");
    await screen.findByLabelText("Book title");
    fireEvent.click(screen.getByRole("button", { name: /Finish my book/ }));
    expect(screen.getByRole("status").textContent).toContain("Add a title");
    expect(
      (screen.getByRole("button", { name: "Remove page" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });
  it("keeps reader direction independent of interface language", async () => {
    renderAt("/read/sample-moon-fox-he");
    const user = userEvent.setup();
    await user.click(
      screen.getAllByRole("button", { name: "Open the book" })[0],
    );
    expect(screen.getByRole("article").getAttribute("dir")).toBe("rtl");
    await user.selectOptions(screen.getByLabelText("Interface language"), "he");
    expect(document.documentElement.dir).toBe("rtl");
    await user.selectOptions(screen.getByLabelText("שפת הממשק"), "en");
    expect(document.documentElement.dir).toBe("ltr");
    expect(screen.getByRole("article").getAttribute("dir")).toBe("rtl");
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(screen.getByRole("status").textContent).toBe("Page 2 of 6");
  });
  it("updates reader labels in the same render as the interface language", async () => {
    renderAt("/read/sample-moon-fox-en");
    const user = userEvent.setup();
    expect(
      screen.getByRole("button", { name: "Page overview" }),
    ).toBeDefined();
    await user.selectOptions(
      screen.getByLabelText("Interface language"),
      "he",
    );
    expect(
      screen.getByRole("button", { name: "מפת עמודים" }),
    ).toBeDefined();
    expect(
      screen.getByRole("button", { name: "קריאה במסך מלא" }),
    ).toBeDefined();
    await user.click(
      screen.getAllByRole("button", { name: "פתיחת הספר" })[0]!,
    );
    expect(screen.getByRole("article").getAttribute("dir")).toBe("ltr");
  });
  it("shows missing-book and unknown-route recovery", () => {
    renderAt("/read/missing");
    expect(
      screen.getByRole("heading", { name: "This book isn’t on your shelf." }),
    ).toBeDefined();
  });
  it("supports a complete support page and native disclosure controls", async () => {
    renderAt("/help");
    const user = userEvent.setup();
    await user.click(screen.getByText("Where are my books saved?"));
    expect(screen.getByText(/Only in this tab/)).toBeDefined();
  });
  it("removes a local book only after a second explicit action", async () => {
    renderAt("/my-books");
    const user = userEvent.setup();
    const articles = screen.getAllByRole("article");
    await user.click(
      within(articles[0]).getByRole("button", { name: /Remove from shelf/ }),
    );
    expect(screen.getAllByRole("article").length).toBe(3);
    await user.click(screen.getByRole("button", { name: "Remove book" }));
    expect(screen.getAllByRole("article").length).toBe(2);
  });
});
