import { describe, expect, it, vi } from "vitest";
import {
  creationIntentKey,
  observeStory,
  startStoryJob,
} from "../src/api/productPorts";
import type { StoryJobPort, StoryOperation } from "../src/api/productPorts";
import { initialDraft, prepareRequest } from "../src/domain/brief";
import { makeSample } from "../src/api/mock";
const request = prepareRequest({
  ...initialDraft,
  name: "Alex",
  theme: "Moon garden",
}).request!;
describe("proposed v3 job ports", () => {
  it('does not retry an ambiguous admission failure or restart after session loss',async()=>{
    const start=vi.fn(async()=>{throw new Error('SESSION_REQUIRED');});
    await expect(startStoryJob({start,get:vi.fn()},request,'intent',new AbortController().signal,vi.fn())).rejects.toThrow('SESSION_REQUIRED');
    expect(start).toHaveBeenCalledTimes(1);
  });
  it('finishes recovery through reads only, even when the server reports a quota failure',async()=>{
    const start=vi.fn();const get=vi.fn(async():Promise<StoryOperation>=>({id:'existing',state:'failed',errorCode:'DAILY_LIMIT_REACHED'}));
    const result=await observeStory({start,get},{id:'existing',state:'running'},new AbortController().signal,vi.fn(),async()=>{});
    expect(start).not.toHaveBeenCalled();expect(get).toHaveBeenCalledTimes(1);expect(result.errorCode).toBe('DAILY_LIMIT_REACHED');
  });
  it("creates an opaque intent key without calling a backend", () => {
    const first = creationIntentKey();
    expect(first).toMatch(/^[A-Za-z0-9_-]+$/);
    expect(first).toHaveLength(43);
    expect(first).not.toBe(creationIntentKey());
  });
  it("observes an existing operation without starting another job", async () => {
    const terminal: StoryOperation = {
      id: "job-1",
      state: "succeeded",
      story: makeSample(request),
    };
    const start = vi.fn(async () => terminal);
    const get = vi.fn(async () => terminal);
    const statuses: string[] = [];
    const result = await startStoryJob(
      { start, get } as StoryJobPort,
      request,
      "intent",
      new AbortController().signal,
      (operation) => statuses.push(operation.state),
    );
    expect(start).toHaveBeenCalledTimes(1);
    expect(get).not.toHaveBeenCalled();
    expect(result.state).toBe("succeeded");
    expect(statuses).toEqual(["succeeded"]);
  });
  it("polls with the server delay and stops on a terminal state", async () => {
    const replies: StoryOperation[] = [
      { id: "job-2", state: "running", retryAfterMs: 250 },
      { id: "job-2", state: "succeeded", story: makeSample(request) },
    ];
    const port: StoryJobPort = {
      start: vi.fn(),
      get: vi.fn(async () => replies.shift()!),
    };
    const waits: number[] = [];
    const statuses: string[] = [];
    const result = await observeStory(
      port,
      { id: "job-2", state: "queued" },
      new AbortController().signal,
      (operation) => statuses.push(operation.state),
      async (ms) => {
        waits.push(ms);
      },
    );
    expect(waits).toEqual([1000, 250]);
    expect(statuses).toEqual(["queued", "running", "succeeded"]);
    expect(result.state).toBe("succeeded");
  });
  it("stops polling when the request is aborted", async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(
      observeStory(
        { start: vi.fn(), get: vi.fn() },
        { id: "job-3", state: "running" },
        controller.signal,
        vi.fn(),
        async () => {},
      ),
    ).rejects.toMatchObject({ name: "AbortError" });
  });
});
