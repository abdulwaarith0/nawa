import { AdminWrapper, AuditWrapper, IamGroupsWrapper, IamPoliciesWrapper } from "@/libs";
import { renderWithLocale } from "@/test/test-utils";
import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Hoisted, per-test-mutable return values for each domain hook + the shell deps.
const s = vi.hoisted(() => ({
  site: { config: undefined, error: undefined, isLoading: false, refresh: vi.fn() } as {
    config: Record<string, unknown> | undefined;
    error: unknown;
    isLoading: boolean;
    refresh: () => void;
  },
  groups: { groups: undefined, error: undefined, isLoading: false, refresh: vi.fn() } as {
    groups: Array<Record<string, unknown>> | undefined;
    error: unknown;
    isLoading: boolean;
    refresh: () => void;
  },
  policies: { policies: undefined, error: undefined, isLoading: false, refresh: vi.fn() } as {
    policies: Array<Record<string, unknown>> | undefined;
    error: unknown;
    isLoading: boolean;
    refresh: () => void;
  },
  audit: { logs: undefined, error: undefined, isLoading: false, refresh: vi.fn() } as {
    logs: Array<Record<string, unknown>> | undefined;
    error: unknown;
    isLoading: boolean;
    refresh: () => void;
  },
}));

vi.mock("@/hooks/Admin", () => ({ useSiteConfig: () => s.site }));
vi.mock("@/hooks/Iam", () => ({ useGroups: () => s.groups, usePolicies: () => s.policies }));
vi.mock("@/hooks/Audit", () => ({ useAuditLogs: () => s.audit }));
vi.mock("@/hooks/Auth", () => ({
  usePermissions: () => ({ has: () => true, isLoading: false, isSignedIn: true }),
  useSession: () => ({ user: null, isLoading: false, isSignedIn: false }),
}));
vi.mock("next/navigation", () => ({ usePathname: () => "/admin" }));
vi.mock("@/lib/apiClient", () => ({
  getApiClient: () => ({ auth: { logout: vi.fn() } }),
}));

beforeEach(() => {
  s.site = { config: undefined, error: undefined, isLoading: false, refresh: vi.fn() };
  s.groups = { groups: undefined, error: undefined, isLoading: false, refresh: vi.fn() };
  s.policies = { policies: undefined, error: undefined, isLoading: false, refresh: vi.fn() };
  s.audit = { logs: undefined, error: undefined, isLoading: false, refresh: vi.fn() };
});

describe("AdminWrapper (site config)", () => {
  it("renders a loading state", () => {
    s.site.isLoading = true;
    renderWithLocale(<AdminWrapper />, "en");
    expect(screen.getAllByText("Loading…").length).toBeGreaterThan(0);
  });

  it("renders an error state with retry", () => {
    s.site.error = new Error("boom");
    renderWithLocale(<AdminWrapper />, "en");
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("renders the key/value rows when loaded", () => {
    s.site.config = { maintenance_mode: false, hero_headline: "Welcome" };
    renderWithLocale(<AdminWrapper />, "en");
    expect(screen.getByText("maintenance_mode")).toBeInTheDocument();
    expect(screen.getByText("hero_headline")).toBeInTheDocument();
    expect(screen.getByText("Welcome")).toBeInTheDocument();
  });
});

describe("IamGroupsWrapper", () => {
  it("renders an empty state when there are no groups", () => {
    s.groups.groups = [];
    renderWithLocale(<IamGroupsWrapper />, "en");
    expect(screen.getByText("No groups yet.")).toBeInTheDocument();
  });

  it("renders each group and flags managed built-ins", () => {
    s.groups.groups = [
      { id: "1", name: "Staff", description: "Internal team", policy_ids: [], managed: true },
      { id: "2", name: "Founders", description: null, policy_ids: [], managed: false },
    ];
    renderWithLocale(<IamGroupsWrapper />, "en");
    expect(screen.getByText("Staff")).toBeInTheDocument();
    expect(screen.getByText("Founders")).toBeInTheDocument();
    expect(screen.getByText("Built-in")).toBeInTheDocument();
  });
});

describe("IamPoliciesWrapper", () => {
  it("renders each policy when loaded", () => {
    s.policies.policies = [
      { id: "1", name: "iam-admin", description: "Manage IAM", statements: [], managed: true },
    ];
    renderWithLocale(<IamPoliciesWrapper />, "en");
    expect(screen.getByText("iam-admin")).toBeInTheDocument();
    expect(screen.getByText("Built-in")).toBeInTheDocument();
  });
});

describe("AuditWrapper", () => {
  it("renders an empty state when there are no entries", () => {
    s.audit.logs = [];
    renderWithLocale(<AuditWrapper />, "en");
    expect(screen.getByText("No audit entries yet.")).toBeInTheDocument();
  });

  it("renders a table row per audit entry", () => {
    s.audit.logs = [
      {
        id: "1",
        actor_id: "u-1",
        actor_type: "user",
        action: "iam.group.create",
        target_type: "group",
        target_id: "g-1",
        status_code: 201,
        duration_ms: 12,
        metadata: null,
        created_at: "2026-07-20T10:00:00Z",
      },
    ];
    renderWithLocale(<AuditWrapper />, "en");
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("iam.group.create")).toBeInTheDocument();
    expect(screen.getByText("u-1")).toBeInTheDocument();
  });
});
