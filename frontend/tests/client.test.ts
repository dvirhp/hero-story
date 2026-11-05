import { describe, expect, it, vi } from "vitest";
import { createHttpStoryService } from "../src/api/client";
import { createMockStoryService, makeSample } from "../src/api/mock";
import { initialDraft, prepareRequest } from "../src/domain/brief";
const request = prepareRequest({
  ...initialDraft,
  name: "Alex",
  theme: "Moon",
}).request!;
const signal = () => new AbortController().signal;
function envelope() {
  return {
    status: "success",
    story: makeSample(request),
    quality: { passed: true },
    resolved_constraints: { page_count: 6 },
  };
}
describe("HTTP seam (mocked fetch only)", () => {
  it("posts exactly the v2 payload once and accepts approved sentence units", async () => {
    const transport = vi
      .fn<typeof fetch>()
      .mockResolvedValue(Response.json(envelope()));
    const story = await createHttpStoryService("/backend/", transport).generate(
      request,
      signal(),
    );
    expect(transport).toHaveBeenCalledTimes(1);
    expect(transport.mock.calls[0][0]).toBe("/backend/v2/stories/generate");
    expect(JSON.parse(transport.mock.calls[0][1]!.body as string)).toEqual(
      request,
    );
    expect(story.pages[0].sentence_units.length).toBe(2);
  });
  it("handles safe error codes without leaking diagnostics or retrying", async () => {
    const transport = vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        Response.json(
          {
            status: "failure",
            error: { code: "BUDGET_EXCEEDED", message: "private diagnostic" },
          },
          { status: 503, headers: { "X-Request-ID": "request-1" } },
        ),
      );
    await expect(
      createHttpStoryService("", transport).generate(request, signal()),
    ).rejects.toMatchObject({
      code: "BUDGET_EXCEEDED",
      requestId: "request-1",
      message: "Story generation could not complete.",
    });
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it.each(["quality", "count", "language", "order", "ids", "units"] as const)(
    "rejects malformed or unapproved %s",
    async (kind) => {
      const body = envelope();
      if (kind === "quality") body.quality.passed = false;
      if (kind === "count") body.story.pages.pop();
      if (kind === "language") body.story.language = "he";
      if (kind === "order") body.story.pages[0].page_number = 2;
      if (kind === "ids")
        body.story.pages[1].page_id = body.story.pages[0].page_id;
      if (kind === "units") body.story.pages[0].sentence_units = [];
      await expect(
        createHttpStoryService(
          "",
          vi.fn().mockResolvedValue(Response.json(body)),
        ).generate(request, signal()),
      ).rejects.toMatchObject({ code: "INVALID_RESPONSE" });
    },
  );
  it("handles non-JSON and network failures", async () => {
    await expect(
      createHttpStoryService(
        "",
        vi.fn().mockResolvedValue(new Response("<html/>")),
      ).generate(request, signal()),
    ).rejects.toMatchObject({ code: "INVALID_RESPONSE" });
    await expect(
      createHttpStoryService(
        "",
        vi.fn().mockRejectedValue(new TypeError("offline")),
      ).generate(request, signal()),
    ).rejects.toMatchObject({ code: "NETWORK_ERROR" });
  });
  it("cancels the local sample without network access", async () => {
    const controller = new AbortController();
    const result = createMockStoryService(100).generate(
      request,
      controller.signal,
    );
    controller.abort();
    await expect(result).rejects.toMatchObject({ name: "AbortError" });
  });
});
