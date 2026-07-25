import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import middleware, { config } from "./middleware";

// Next.js applies `config.matcher` BEFORE ever invoking the middleware
// function — a path that doesn't match never reaches the logic tested below
// at all. Regression coverage for the matcher itself, since a prior version
// of this pattern let /brand/nawa-emblem.svg (and any other public/ static
// asset) fall through to the middleware function, which treated it as a
// protected app route and redirected it to /login, breaking every image on
// every page.
function matcherExcludes(pathname: string): boolean {
  const pattern = new RegExp(`^${config.matcher[0]}$`);
  return !pattern.test(pathname);
}

function base64url(obj: object): string {
  return Buffer.from(JSON.stringify(obj))
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function fakeSessionJwt(perms: string[], expiresInSeconds = 3600): string {
  const payload = { sub: "1", perms, exp: Math.floor(Date.now() / 1000) + expiresInSeconds };
  return `${base64url({ alg: "HS256" })}.${base64url(payload)}.signature`;
}

function request(pathname: string, cookie?: string): NextRequest {
  const headers = cookie ? { cookie: `nw_session=${cookie}` } : undefined;
  return new NextRequest(new URL(pathname, "http://localhost:3000"), { headers });
}

describe("edge middleware", () => {
  it("redirects an anonymous visitor off a protected route to /login?next=...", () => {
    const res = middleware(request("/intake"));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost:3000/login?next=%2Fintake");
  });

  it("bounces a signed-in user off /login to their permission-based home", () => {
    const res = middleware(request("/login", fakeSessionJwt(["nawa:console:intake"])));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost:3000/intake");
  });

  it("lets a signed-in user with no gated permission reach a protected route (fine-grained gating stays client-side)", () => {
    const res = middleware(request("/admin", fakeSessionJwt([])));
    expect(res.headers.get("location")).toBeNull();
  });

  it("lets an anonymous visitor reach public routes", () => {
    expect(middleware(request("/")).headers.get("location")).toBeNull();
    expect(middleware(request("/styleguide")).headers.get("location")).toBeNull();
  });

  it("treats an expired session cookie as signed out", () => {
    const res = middleware(request("/intake", fakeSessionJwt([], -10)));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost:3000/login?next=%2Fintake");
  });

  it("does not bounce an anonymous visitor away from the guest-only pages", () => {
    const res = middleware(request("/request-access"));
    expect(res.headers.get("location")).toBeNull();
  });

  describe("matcher pattern", () => {
    it("excludes public/ static assets by file extension", () => {
      expect(matcherExcludes("/brand/nawa-emblem.svg")).toBe(true);
      expect(matcherExcludes("/auth/nawa-dashboard-preview.png")).toBe(true);
      expect(matcherExcludes("/favicon.ico")).toBe(true);
    });

    it("excludes API routes and Next.js internals", () => {
      expect(matcherExcludes("/api/auth/me")).toBe(true);
      expect(matcherExcludes("/_next/static/chunks/main.js")).toBe(true);
      expect(matcherExcludes("/_next/image")).toBe(true);
      expect(matcherExcludes("/__nextjs_original-stack-frames")).toBe(true);
    });

    it("does not exclude real app routes", () => {
      expect(matcherExcludes("/login")).toBe(false);
      expect(matcherExcludes("/intake")).toBe(false);
      expect(matcherExcludes("/dashboard")).toBe(false);
    });
  });
});
