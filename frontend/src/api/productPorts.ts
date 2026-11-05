import type { StoryRequestV2, StoryV2 } from "./contracts";
/** Proposed integration ports derived from Agent 3 API_CONTRACTS.md, not executable OpenAPI or live routes. */
export interface SessionContext {
  mode: "anonymous" | "account";
  expires_at: string;
  absolute_expires_at: string;
  csrf_token: string;
}
export interface UsageBucket {
  limit: number;
  consumed: number;
  reserved: number;
  remaining: number;
}
export interface DailyUsage {
  policy_version: string;
  timezone: "UTC";
  day: string;
  reset_at: string;
  capabilities: {
    story_generation: UsageBucket;
    image_generation: UsageBucket;
  };
}
export interface AccessPort {
  session(signal: AbortSignal): Promise<SessionContext>;
  usage(signal: AbortSignal): Promise<DailyUsage>;
}
/** State names remain provisional until the joint Agent 1/3 async design is approved. */
export type StoryOperation = {
  id: string;
  state:
    | "queued"
    | "running"
    | "succeeded"
    | "failed"
    | "cancelled"
    | "unknown";
  story?: StoryV2;
  errorCode?:
    | "SESSION_REQUIRED"
    | "DAILY_LIMIT_REACHED"
    | "ADMISSION_UNAVAILABLE"
    | "GENERATION_FAILED";
  retryAfterMs?: number;
};
export interface StoryJobPort {
  start(
    request: StoryRequestV2,
    intentKey: string,
    signal: AbortSignal,
  ): Promise<StoryOperation>;
  get(id: string, signal: AbortSignal): Promise<StoryOperation>;
}
export function creationIntentKey() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return btoa(String.fromCharCode(...bytes))
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");
}
export async function observeStory(
  port: StoryJobPort,
  operation: StoryOperation,
  signal: AbortSignal,
  onStatus: (operation: StoryOperation) => void,
  wait: (ms: number, signal: AbortSignal) => Promise<void> = abortableWait,
): Promise<StoryOperation> {
  let current = operation;
  for (let reads = 0; reads <= 120; reads++) {
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");
    onStatus(current);
    if (["succeeded", "failed", "cancelled", "unknown"].includes(current.state))
      return current;
    if (reads === 120) break;
    await wait(
      Math.min(10000, Math.max(250, current.retryAfterMs ?? 1000)),
      signal,
    );
    current = await port.get(current.id, signal);
  }
  return { ...current, state: "unknown" };
}
function abortableWait(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const abort = () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", abort);
      resolve();
    }, ms);
    signal.addEventListener("abort", abort, { once: true });
  });
}
/** One intentional POST only. Recovery uses observeStory with the existing operation, never another start. */
export async function startStoryJob(
  port: StoryJobPort,
  request: StoryRequestV2,
  intentKey: string,
  signal: AbortSignal,
  onStatus: (operation: StoryOperation) => void,
) {
  if (signal.aborted) throw new DOMException("Aborted", "AbortError");
  const operation = await port.start(request, intentKey, signal);
  return observeStory(port, operation, signal, onStatus);
}
