// The browser-side API client. Calls relative /api/* (proxied by next.config to
// the FastAPI service under /api/v1), so the session stays a first-party
// httpOnly cookie — no bearer token in the browser. On an unrecoverable auth
// error we bounce to the login page.

import { isPublicPath } from "@/helpers/isPublicPath";
import { type ApiClient, createApiClient } from "@nawa/api-client";
import { PUBLIC_PREFIXES, Routes } from "@nawa/contracts";

let client: ApiClient | null = null;

export function getApiClient(): ApiClient {
  if (client) return client;
  client = createApiClient({
    baseUrl: "/api",
    credentials: "include",
    onAuthError: () => {
      // A 401 on a public page (e.g. AuthShell's own session probe on
      // /login or /request-access) is expected for an anonymous visitor —
      // only force-navigate to login from a page that actually needs a
      // session. Without this check, the guest-accessible auth pages'
      // own /auth/me check would immediately bounce themselves to /login.
      if (typeof window === "undefined") return;
      if (isPublicPath(window.location.pathname, PUBLIC_PREFIXES)) return;
      const next = encodeURIComponent(window.location.pathname);
      window.location.href = `${Routes.login}?next=${next}`;
    },
  });
  return client;
}
