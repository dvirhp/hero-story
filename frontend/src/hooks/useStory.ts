import { useEffect, useRef } from "react";
import type { StoryRequestV2, StoryService, StoryV2 } from "../api/contracts";
export function useStory(service: StoryService) {
  const active = useRef<AbortController | null>(null);
  const cancel = () => {
    active.current?.abort();
    active.current = null;
  };
  useEffect(() => () => active.current?.abort(), []);
  const generate = async (
    request: StoryRequestV2,
  ): Promise<{ story: StoryV2 } | { error: true } | null> => {
    cancel();
    const controller = new AbortController();
    active.current = controller;
    try {
      const story = await service.generate(request, controller.signal);
      return !controller.signal.aborted && active.current === controller
        ? { story }
        : null;
    } catch {
      return !controller.signal.aborted && active.current === controller
        ? { error: true }
        : null;
    } finally {
      if (active.current === controller) active.current = null;
    }
  };
  return { generate, cancel };
}
