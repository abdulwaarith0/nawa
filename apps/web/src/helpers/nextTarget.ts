// Shared by the auth pages: the post-login/post-signup/guest-bounce
// destination (design-system §13). Reads live browser state at call time, so
// this stays a plain function — memoizing it would go stale across
// navigations. `perms` should be the just-authenticated session's effective
// permissions so the fallback matches the edge middleware's own
// homeForPermissions call exactly.
import { Routes, homeForPermissions } from "@nawa/contracts";

export function nextTarget(perms: string[] = []): string {
  if (typeof window === "undefined") return Routes.dashboard;
  const next = new URLSearchParams(window.location.search).get("next");
  // Only allow same-origin relative paths.
  return next?.startsWith("/") ? next : homeForPermissions(perms);
}
