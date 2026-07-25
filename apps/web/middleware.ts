// Edge gate (design-system §13, DoD item 12): a coarse, session-presence-only
// check. Decodes (never verifies — no secret at the edge) the `nw_session`
// JWT's `perms` claim purely to compute the guest-only-bounce/post-login
// landing surface; it is a UX hint, not an authorization boundary (§8 — the
// API's live re-resolution is the law). Fine-grained per-permission gating
// (e.g. a Founder hitting /admin) is left to the client-side <Guard/> so the
// page still renders (200) with a localized denied panel, never a redirect
// loop or blank page.

import { isPublicPath } from "@/helpers/isPublicPath";
import { GUEST_ONLY_PREFIXES, PUBLIC_PREFIXES, Routes, homeForPermissions } from "@nawa/contracts";
import { type NextRequest, NextResponse } from "next/server";

export const config = {
  // __nextjs_* covers dev-only internal endpoints (error-overlay stack-frame
  // lookups, etc.) — without this exclusion a real page error's dev overlay
  // triggers a redirect loop through /login instead of ever showing.
  // `.*\..*` (any path containing a dot) is the standard Next.js pattern for
  // excluding static files served from public/ — without it, requests for
  // /brand/nawa-emblem.svg etc. get treated as protected app routes and
  // redirected to /login, breaking every image on every page.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|__nextjs_|.*\\..*).*)"],
};

interface SessionClaims {
  perms: string[];
}

function decodeSessionCookie(token: string | undefined): SessionClaims | null {
  if (!token) return null;
  const payload = token.split(".")[1];
  if (!payload) return null;
  try {
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const claims = JSON.parse(atob(padded));
    if (typeof claims.exp !== "number" || claims.exp * 1000 <= Date.now()) return null;
    return { perms: Array.isArray(claims.perms) ? claims.perms : [] };
  } catch {
    return null;
  }
}

export default function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const claims = decodeSessionCookie(request.cookies.get("nw_session")?.value);

  if (isPublicPath(pathname, GUEST_ONLY_PREFIXES)) {
    return claims
      ? NextResponse.redirect(new URL(homeForPermissions(claims.perms), request.url))
      : NextResponse.next();
  }

  if (isPublicPath(pathname, PUBLIC_PREFIXES)) {
    return NextResponse.next();
  }

  if (!claims) {
    const loginUrl = new URL(Routes.login, request.url);
    loginUrl.searchParams.set("next", pathname + search);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}
