// The const tree of web UI paths (design-system §8 surface map). Hand-written;
// the single source of truth for links/redirects in the web app.

export const Routes = {
  home: "/",
  login: "/login",
  requestAccess: "/request-access",
  forgotPassword: "/forgot-password",
  resetPassword: "/reset-password",
  onboarding: "/onboarding",
  dashboard: "/dashboard",
  profile: (handle: string) => `/profile/${handle}`,
  intake: {
    home: "/intake",
    upload: "/intake/upload",
    audit: "/intake/audit",
    cycle: (cycleId: string) => `/intake/cycles/${cycleId}`,
    application: (id: string) => `/intake/applications/${id}`,
  },
  journey: {
    home: "/journey",
    digests: "/journey/digests",
  },
  community: {
    home: "/community",
    requests: "/community/requests",
    opportunities: "/community/opportunities",
    mentors: "/community/mentors",
  },
  reports: {
    home: "/reports",
    portfolio: "/reports/portfolio",
    generate: "/reports/generate",
  },
  admin: {
    home: "/admin",
    iamGroups: "/admin/iam/groups",
    iamPolicies: "/admin/iam/policies",
    audit: "/admin/audit",
    accessRequests: "/admin/access-requests",
  },
  styleguide: "/styleguide",
} as const;

// Public prefixes the edge gate lets through without a session. `/styleguide`
// is the dev-only kit gallery (design-system §14) — the Playwright DoD suite
// exercises it unauthenticated, so it must stay public.
export const PUBLIC_PREFIXES = [
  "/",
  "/login",
  "/request-access",
  "/forgot-password",
  "/reset-password",
  "/styleguide",
] as const;
export const GUEST_ONLY_PREFIXES = [
  "/login",
  "/request-access",
  "/forgot-password",
  "/reset-password",
] as const;
