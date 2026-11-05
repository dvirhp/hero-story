import { useSyncExternalStore } from "react";
export type Route =
  | {
      page:
        | "home"
        | "discover"
        | "create"
        | "library"
        | "about"
        | "help"
        | "privacy"
        | "loading"
        | "error"
        | "not-found";
    }
  | { page: "cart" | "checkout" | "orders" }
  | {
      page:
        | "product"
        | "personalize"
        | "reader"
        | "editor"
        | "format"
        | "order"
        | "confirmation";
      id: string;
    };
const simple: Record<
  string,
  Exclude<
    Route["page"],
    | "product"
    | "personalize"
    | "reader"
    | "editor"
    | "format"
    | "order"
    | "confirmation"
  >
> = {
  "/": "home",
  "/books": "discover",
  "/create/ai": "create",
  "/my-books": "library",
  "/about": "about",
  "/help": "help",
  "/privacy": "privacy",
  "/generating": "loading",
  "/generation-error": "error",
  "/cart": "cart",
  "/checkout": "checkout",
  "/orders": "orders",
};
export function parseRoute(hash: string): Route {
  const path = hash.replace(/^#/, "").split("?")[0] || "/";
  if (simple[path]) return { page: simple[path] };
  const match = path.match(
    /^\/(books|personalize|read|studio|format|orders|confirmation)\/([a-zA-Z0-9_-]+)$/,
  );
  if (match)
    return {
      page: (
        {
          books: "product",
          personalize: "personalize",
          read: "reader",
          studio: "editor",
          format: "format",
          orders: "order",
          confirmation: "confirmation",
        } as const
      )[
        match[1] as
          | "books"
          | "personalize"
          | "read"
          | "studio"
          | "format"
          | "orders"
          | "confirmation"
      ],
      id: match[2],
    };
  return { page: "not-found" };
}
export function go(path: string) {
  if (location.hash === `#${path}`) return;
  location.hash = path;
}
const subscribe = (callback: () => void) => {
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
};
export function useRoute() {
  const hash = useSyncExternalStore(
    subscribe,
    () => window.location.hash,
    () => "",
  );
  return { route: parseRoute(hash), key: hash };
}
