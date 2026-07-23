// The const tree of web UI paths (design-system §8 surface map). Hand-written;
// the single source of truth for links/redirects in the web app.

export const Routes = {
  home: "/",
  login: "/login",
  signup: "/signup",
  forgotPassword: "/forgot-password",
  onboarding: "/onboarding",
  profile: (handle: string) => `/profile/${handle}`,
  intake: {
    home: "/intake",
    upload: "/intake/upload",
    shortlist: "/intake/shortlist",
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
  },
  styleguide: "/styleguide",
} as const;

// Public prefixes the edge gate lets through without a session.
export const PUBLIC_PREFIXES = ["/", "/login", "/signup", "/forgot-password"] as const;
export const GUEST_ONLY_PREFIXES = ["/login", "/signup", "/forgot-password"] as const;
