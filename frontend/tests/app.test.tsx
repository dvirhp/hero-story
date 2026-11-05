import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../src/App";
import { makeSample } from "../src/api/mock";
import type { StoryService } from "../src/api/contracts";
afterEach(cleanup);
beforeEach(() => vi.spyOn(window, "scrollTo").mockImplementation(() => {}));
describe("story creation and reading", () => {
  it("completes a local request, navigates pages and preserves the brief", async () => {
    const user = userEvent.setup();
    const generate = vi
      .fn<StoryService["generate"]>()
      .mockImplementation(async (request) => makeSample(request));
    render(<App service={{ generate }} />);
    await user.click(
      screen.getAllByRole("button", { name: /Create a story/ })[0],
    );
    await user.type(screen.getByLabelText("Child’s name"), "Alex");
    await user.type(
      screen.getByLabelText("What is the story about?"),
      "Moon garden",
    );
    await user.click(screen.getByRole("button", { name: /Make our story/ }));
    await screen.findByRole("heading", {
      name: "The seed that held the moonlight",
    });
    expect(generate).toHaveBeenCalledTimes(1);
    expect(
      (
        screen.getByRole("button", {
          name: "Previous page",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(screen.getByRole("status").textContent).toBe("Page 2 of 6");
    for (let i = 0; i < 4; i++)
      await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(
      (screen.getByRole("button", { name: "Next page" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    await user.click(screen.getByRole("button", { name: /Create another/ }));
    expect(
      (screen.getByLabelText("Child’s name") as HTMLInputElement).value,
    ).toBe("Alex");
  });
  it("renders validation before any service call and focuses the invalid field", async () => {
    const generate = vi.fn();
    render(<App service={{ generate }} />);
    fireEvent.click(
      screen.getAllByRole("button", { name: /Create a story/ })[0],
    );
    fireEvent.click(screen.getByRole("button", { name: /Make our story/ }));
    expect(screen.getByRole("alert").textContent).toContain("highlighted");
    expect(generate).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(document.activeElement).toBe(
        screen.getByLabelText("Child’s name"),
      ),
    );
  });
  it("switches interface direction independently from story language", async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("Interface language"), {
      target: { value: "he" },
    });
    expect(document.documentElement.dir).toBe("rtl");
    expect(document.documentElement.lang).toBe("he");
    fireEvent.click(screen.getByRole("button", { name: /קריאת סיפור לדוגמה/ }));
    expect(screen.getByRole("article").getAttribute("dir")).toBe("rtl");
    fireEvent.change(screen.getByLabelText("שפת הממשק"), {
      target: { value: "en" },
    });
    expect(document.documentElement.dir).toBe("ltr");
    expect(screen.getByRole("article").getAttribute("dir")).toBe("rtl");
  });
  it("shows loading, aborts on cancel and ignores a stale result", async () => {
    let resolve!: (story: ReturnType<typeof makeSample>) => void;
    const generate = vi.fn<StoryService["generate"]>().mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    render(<App service={{ generate }} />);
    fireEvent.click(
      screen.getAllByRole("button", { name: /Create a story/ })[0],
    );
    fireEvent.change(screen.getByLabelText("Child’s name"), {
      target: { value: "Alex" },
    });
    fireEvent.change(screen.getByLabelText("What is the story about?"), {
      target: { value: "Moon" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Make our story/ }));
    expect(screen.getByRole("status").textContent).toContain(
      "world is taking shape",
    );
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(generate.mock.calls[0][1].aborted).toBe(true);
    resolve(makeSample(generate.mock.calls[0][0]));
    await waitFor(() =>
      expect(screen.getByLabelText("Child’s name")).toBeDefined(),
    );
    expect(screen.queryByRole("article")).toBeNull();
  });
  it("returns from a service failure without losing the brief", async () => {
    const generate = vi
      .fn()
      .mockRejectedValue(new Error("private server diagnostic"));
    render(<App service={{ generate }} />);
    fireEvent.click(
      screen.getAllByRole("button", { name: /Create a story/ })[0],
    );
    fireEvent.change(screen.getByLabelText("Child’s name"), {
      target: { value: "Alex" },
    });
    fireEvent.change(screen.getByLabelText("What is the story about?"), {
      target: { value: "Moon" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Make our story/ }));
    await screen.findByRole("alert");
    expect(screen.queryByText("private server diagnostic")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Return to my brief" }));
    expect(
      (screen.getByLabelText("Child’s name") as HTMLInputElement).value,
    ).toBe("Alex");
  });
  it("shows recoverable error and empty reader states", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Preview error" }));
    expect(screen.getByRole("alert").textContent).toContain("another moment");
    fireEvent.click(screen.getByRole("button", { name: "Return to my brief" }));
    expect(screen.getByLabelText("Child’s name")).toBeDefined();
    fireEvent.click(
      screen.getByRole("button", { name: "Preview empty reader" }),
    );
    expect(
      screen.getByRole("heading", { name: "Your next adventure is waiting." }),
    ).toBeDefined();
  });
});
