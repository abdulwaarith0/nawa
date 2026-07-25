import { DashboardWrapper } from "@/libs";
import { renderWithLocale } from "@/test/test-utils";
import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard" }));
vi.mock("@/hooks/Auth", () => ({
  usePermissions: () => ({ has: () => false, isLoading: false, isSignedIn: false }),
  useSession: () => ({ user: null, isLoading: false, isSignedIn: false }),
}));
vi.mock("@/lib/apiClient", () => ({
  getApiClient: () => ({ auth: { logout: vi.fn() } }),
}));

const mockUseDashboard = vi.fn();
vi.mock("@/hooks/Dashboard", () => ({
  useDashboard: () => mockUseDashboard(),
}));

const BASE = {
  user: null,
  isSignedIn: false,
  isLoading: false,
  modules: [] as Array<{ key: string; gate: string; href: string }>,
  hasIntake: false,
  cyclesLoading: false,
  featuredCycle: null,
  stats: null,
  statsLoading: false,
  rail: [] as Array<{
    applicationId: string;
    applicantName: string;
    score: number | null;
    decision: string;
    hiddenGem: boolean;
  }>,
};

describe("DashboardWrapper", () => {
  afterEach(() => mockUseDashboard.mockReset());

  it("shows a loading state while the session resolves", () => {
    mockUseDashboard.mockReturnValue({ ...BASE, isLoading: true });
    renderWithLocale(<DashboardWrapper />, "en");
    expect(screen.getAllByText("Loading…").length).toBeGreaterThan(0);
  });

  it("prompts a signed-out visitor to sign in", () => {
    mockUseDashboard.mockReturnValue({ ...BASE });
    renderWithLocale(<DashboardWrapper />, "en");
    expect(screen.getByText("Sign in to see your dashboard")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute(
      "href",
      "/login?next=/dashboard",
    );
  });

  it("shows an empty state for a signed-in user with no module access", () => {
    mockUseDashboard.mockReturnValue({
      ...BASE,
      user: { full_name: "Karim", effective: [] },
      isSignedIn: true,
    });
    renderWithLocale(<DashboardWrapper />, "en");
    expect(screen.getByText("Nothing here yet")).toBeInTheDocument();
  });

  it("falls back to the module-link grid for a session without intake access", () => {
    mockUseDashboard.mockReturnValue({
      ...BASE,
      user: { full_name: "Dana Al-Emadi", effective: [] },
      isSignedIn: true,
      modules: [{ key: "reports", gate: "nawa:console:reports", href: "/reports" }],
      hasIntake: false,
    });
    renderWithLocale(<DashboardWrapper />, "en");
    expect(screen.getByText("Good morning, Dana Al-Emadi")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Reports & KPIs/ })).toHaveAttribute(
      "href",
      "/reports",
    );
    // Intake-only affordances stay hidden without the permission.
    expect(screen.queryByText("New batch")).not.toBeInTheDocument();
  });

  it("shows an honest empty state for an intake-permitted session with no cycle yet", () => {
    mockUseDashboard.mockReturnValue({
      ...BASE,
      user: { full_name: "Dana", effective: [] },
      isSignedIn: true,
      modules: [{ key: "intake", gate: "nawa:console:intake", href: "/intake" }],
      hasIntake: true,
      featuredCycle: null,
    });
    renderWithLocale(<DashboardWrapper />, "en");
    expect(screen.getByText("No intake cycle yet")).toBeInTheDocument();
  });

  it("renders the real screening overview from shortlist-derived stats", () => {
    mockUseDashboard.mockReturnValue({
      ...BASE,
      user: { full_name: "Dana Al-Emadi", effective: [] },
      isSignedIn: true,
      modules: [{ key: "intake", gate: "nawa:console:intake", href: "/intake" }],
      hasIntake: true,
      featuredCycle: { id: "cycle-1", status: "active" },
      stats: {
        applications: 120,
        shortlisted: 18,
        hiddenGems: 4,
        flagged: 3,
        scored: 110,
        inReview: 7,
        gaugePercent: 92,
      },
      rail: [
        {
          applicationId: "app-1",
          applicantName: "Sara Al-Mansoori",
          score: 9.1,
          decision: "shortlist",
          hiddenGem: false,
        },
      ],
    });
    renderWithLocale(<DashboardWrapper />, "en");
    expect(screen.getByText("Good morning, Dana Al-Emadi")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "New batch" })).toHaveAttribute("href", "/intake");
    expect(screen.getByText("120")).toBeInTheDocument();
    expect(screen.getByText("92%")).toBeInTheDocument();
    expect(screen.getByText("Sara Al-Mansoori")).toBeInTheDocument();
    expect(screen.getByText("shortlist")).toBeInTheDocument();
  });

  it("renders Arabic labels under ar", () => {
    mockUseDashboard.mockReturnValue({ ...BASE });
    renderWithLocale(<DashboardWrapper />, "ar");
    expect(screen.getByText("سجّل الدخول لرؤية لوحتك الرئيسية")).toBeInTheDocument();
  });
});
