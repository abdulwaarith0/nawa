// The browser-side API client. Calls relative /api/* (proxied by next.config to
// the FastAPI service under /api/v1), so the session stays a first-party
// httpOnly cookie — no bearer token in the browser. On an unrecoverable auth
// error we bounce to the login page.

import { type ApiClient, createApiClient } from "@nawa/api-client";
import { Routes } from "@nawa/contracts";

let client: ApiClient | null = null;

export function getApiClient(): ApiClient {
  if (client) return client;
  client = createApiClient({
    baseUrl: "/api",
    credentials: "include",
    onAuthError: () => {
      if (typeof window !== "undefined" && window.location.pathname !== Routes.login) {
        const next = encodeURIComponent(window.location.pathname);
        window.location.href = `${Routes.login}?next=${next}`;
      }
    },
  });
  return client;
}
