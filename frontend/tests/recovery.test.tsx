import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  render,
  renderHook,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../src/App";
import { useCommerce } from "../src/commerce/useCommerce";
import { catalog, sampleBook } from "../src/data/catalog";
import { useLibrary } from "../src/hooks/useLibrary";
import {isBook,readTab,writeTab,clearTab} from '../src/state/tabRecovery';
const consentKey = "storyforge.tab.v1.consent";
function renderAt(path: string) {
  window.history.replaceState(null, "", `#${path}`);
  return render(<App />);
}
beforeEach(() => {
  sessionStorage.clear();
  window.history.replaceState(null, "", "#/");
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
});
afterEach(cleanup);
describe("consent-based tab recovery", () => {
  it('ignores malformed, oversized and invalid nested saved books and preserves unrelated storage',()=>{
    sessionStorage.setItem('unrelated','keep');
    expect(writeTab('working',sampleBook(catalog[0],'en'))).toBe(true);
    expect(sessionStorage.getItem('storyforge.tab.v1.working')).toBeNull();
    sessionStorage.setItem(consentKey,'yes');
    sessionStorage.setItem('storyforge.tab.v1.working','{');expect(readTab('working',isBook)).toBeNull();
    sessionStorage.setItem('storyforge.tab.v1.working','x'.repeat(1000001));expect(readTab('working',isBook)).toBeNull();
    const invalid={...sampleBook(catalog[0],'en'),childName:{unsafe:'object'}};
    expect(isBook(invalid)).toBe(false);
    clearTab();expect(sessionStorage.getItem('unrelated')).toBe('keep');
  });
  it("keeps drafts in memory only until the adult opts in", async () => {
    renderAt("/studio/new");
    const user = userEvent.setup();
    await screen.findByLabelText("Book title");
    await user.type(screen.getByLabelText("Book title"), "Private draft");
    expect(sessionStorage.length).toBe(0);
  });
  it("restores a working draft and the AI brief after opt-in", async () => {
    renderAt("/studio/new");
    const user = userEvent.setup();
    await screen.findByLabelText("Book title");
    await user.type(screen.getByLabelText("Book title"), "Recovered draft");
    await user.click(
      screen.getByLabelText("Keep my books and bag on refresh in this tab"),
    );
    await waitFor(() =>
      expect(sessionStorage.getItem("storyforge.tab.v1.working")).toContain(
        "Recovered draft",
      ),
    );
    await waitFor(() =>
      expect(window.location.hash).toMatch(/^#\/studio\/[^/]+$/),
    );
    const studioHash = window.location.hash.slice(1);
    cleanup();
    renderAt(studioHash);
    await screen.findByLabelText("Book title");
    expect(
      (screen.getByLabelText("Book title") as HTMLInputElement).value,
    ).toBe("Recovered draft");

    cleanup();
    renderAt("/create/ai");
    await user.type(await screen.findByLabelText("Child’s name"), "Nora");
    await waitFor(() =>
      expect(sessionStorage.getItem("storyforge.tab.v1.brief")).toContain(
        "Nora",
      ),
    );
    cleanup();
    renderAt("/create/ai");
    expect(
      ((await screen.findByLabelText("Child’s name")) as HTMLInputElement)
        .value,
    ).toBe("Nora");
  });
  it("restores saved books and the demo bag, while orders stay in memory", async () => {
    sessionStorage.setItem(consentKey, "yes");
    const library = renderHook(() => useLibrary(true));
    act(() =>
      library.result.current.save({
        ...sampleBook(catalog[0], "en"),
        id: "recovered-book",
        title: "Recovered book",
      }),
    );
    await waitFor(() =>
      expect(sessionStorage.getItem("storyforge.tab.v1.books")).toContain(
        "Recovered book",
      ),
    );
    library.unmount();
    const restoredLibrary = renderHook(() => useLibrary(true));
    expect(
      restoredLibrary.result.current.books.some(
        (book) => book.id === "recovered-book",
      ),
    ).toBe(true);
    restoredLibrary.unmount();

    const cart = renderHook(() => useCommerce(true));
    act(() =>
      cart.result.current.add(sampleBook(catalog[0], "en"), "hardcover", 2),
    );
    await waitFor(() =>
      expect(sessionStorage.getItem("storyforge.tab.v1.bag")).toContain(
        "hardcover",
      ),
    );
    cart.unmount();
    const restoredCart = renderHook(() => useCommerce(true));
    expect(restoredCart.result.current.lines).toHaveLength(1);
    expect(restoredCart.result.current.count).toBe(2);
    expect(restoredCart.result.current.orders).toEqual([]);
  });
  it("clears every saved recovery key when consent is withdrawn", async () => {
    renderAt("/studio/new");
    const user = userEvent.setup();
    await screen.findByLabelText("Book title");
    await user.click(
      screen.getByLabelText("Keep my books and bag on refresh in this tab"),
    );
    await waitFor(() => expect(sessionStorage.length).toBeGreaterThan(0));
    await user.click(
      screen.getByRole("button", { name: "Clear saved tab progress" }),
    );
    expect(sessionStorage.length).toBe(0);
    expect(
      screen.queryByRole("button", { name: "Clear saved tab progress" }),
    ).toBeNull();
  });
});
