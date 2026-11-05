import type { StoryRequestV2, StoryService, StoryV2 } from "./contracts";
export class StoryServiceError extends Error {
  constructor(
    public readonly code: string,
    public readonly requestId?: string,
  ) {
    super("Story generation could not complete.");
  }
}
function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
/** Validate consumed fields before rendering; no casts of untrusted JSON into a successful story. */
export function parseStory(value: unknown, request: StoryRequestV2): StoryV2 {
  if (
    !record(value) ||
    value.schema_version !== "2" ||
    typeof value.title !== "string" ||
    !value.title.trim() ||
    value.language !== request.language ||
    value.direction !== (request.language === "he" ? "rtl" : "ltr") ||
    typeof value.profile_id !== "string" ||
    typeof value.profile_version !== "string" ||
    value.page_count !== request.page_count ||
    !Array.isArray(value.pages) ||
    value.pages.length !== request.page_count ||
    (request.requested_title && value.title !== request.requested_title)
  )
    throw new StoryServiceError("INVALID_RESPONSE");
  const ids = new Set<string>();
  const pages = value.pages.map((page: unknown, i: number) => {
    if (
      !record(page) ||
      typeof page.page_id !== "string" ||
      !page.page_id.trim() ||
      ids.has(page.page_id) ||
      page.page_number !== i + 1 ||
      page.target_id !== (request.structure?.targets[i]?.target_id ?? null) ||
      !Array.isArray(page.sentence_units) ||
      !page.sentence_units.length ||
      !page.sentence_units.every(
        (unit: unknown) => typeof unit === "string" && unit.trim(),
      )
    )
      throw new StoryServiceError("INVALID_RESPONSE");
    ids.add(page.page_id);
    return {
      page_id: page.page_id,
      page_number: i + 1,
      target_id: page.target_id as string | null,
      sentence_units: page.sentence_units as string[],
    };
  });
  return {
    schema_version: "2",
    title: value.title,
    language: request.language,
    direction: request.language === "he" ? "rtl" : "ltr",
    profile_id: value.profile_id,
    profile_version: value.profile_version,
    page_count: request.page_count,
    pages,
  };
}
/** Explicit opt-in seam for later integration. App never constructs this client. No automatic retries. */
export function createHttpStoryService(
  baseUrl = "",
  transport: typeof fetch = fetch,
): StoryService {
  return {
    async generate(request, signal) {
      let response: Response;
      try {
        response = await transport(
          `${baseUrl.replace(/\/$/, "")}/v2/stories/generate`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(request),
            signal,
            cache: "no-store",
            credentials: "omit",
          },
        );
      } catch (error) {
        if (signal.aborted) throw new DOMException("Cancelled", "AbortError");
        throw error instanceof StoryServiceError
          ? error
          : new StoryServiceError("NETWORK_ERROR");
      }
      let body: unknown;
      try {
        body = await response.json();
      } catch {
        throw new StoryServiceError("INVALID_RESPONSE");
      }
      const requestId = response.headers.get("X-Request-ID") ?? undefined;
      if (!record(body))
        throw new StoryServiceError("INVALID_RESPONSE", requestId);
      if (!response.ok || body.status === "failure") {
        // Surface only code and bounded request ID to callers; never display server diagnostics.
        const code =
          record(body.error) && typeof body.error.code === "string"
            ? body.error.code
            : "HTTP_ERROR";
        throw new StoryServiceError(code, requestId);
      }
      if (
        body.status !== "success" ||
        !record(body.quality) ||
        body.quality.passed !== true ||
        !record(body.resolved_constraints) ||
        body.resolved_constraints.page_count !== request.page_count
      )
        throw new StoryServiceError("INVALID_RESPONSE", requestId);
      return parseStory(body.story, request);
    },
  };
}
