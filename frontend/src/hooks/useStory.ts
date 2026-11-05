import { useEffect, useRef, useState } from "react";
import type { StoryRequestV2, StoryService, StoryV2 } from "../api/contracts";
export type StoryState =
  | { screen: "landing" | "create" | "loading" | "error" }
  | { screen: "reader"; story: StoryV2 | null };
export function useStory(service: StoryService) {
  const [state, setState] = useState<StoryState>({ screen: "landing" });
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  const navigate = (state: StoryState) => {
    active.current?.abort();
    active.current = null;
    setState(state);
  };
  const generate = async (request: StoryRequestV2) => {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setState({ screen: "loading" });
    try {
      const story = await service.generate(request, controller.signal);
      if (!controller.signal.aborted && active.current === controller)
        setState({ screen: "reader", story });
    } catch {
      if (!controller.signal.aborted && active.current === controller)
        setState({ screen: "error" });
    } finally {
      if (active.current === controller) active.current = null;
    }
  };
  return { state, navigate, generate };
}
