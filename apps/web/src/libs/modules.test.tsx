import { CommunityWrapper, IntakeWrapper, JourneyWrapper, ReportsWrapper } from "@/libs";
import { renderWithLocale } from "@/test/test-utils";
import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// The module scaffolds compose the shells, which read session + routing. Stub
// those so the wrappers render their titles + the coming-soon placeholder.
const perm = vi.hoisted(() => ({ allow: true }));
vi.mock("@/hooks/Auth", () => ({
  useSession: () => ({ user: null, isSignedIn: false }),
  usePermissions: () => ({ has: () => perm.allow, isLoading: false, isSignedIn: true }),
}));
vi.mock("next/navigation", () => ({ usePathname: () => "/intake" }));

// IntakeWrapper is real (chunk 12) rather than a ComingSoon scaffold — stub
// its data hooks so this render is a pure static-shell check, same as the
// admin wrappers' own test convention.
vi.mock("@/hooks/Intake", () => ({
  useCycles: () => ({ cycles: [], error: undefined, isLoading: false, refresh: vi.fn() }),
  useUpload: () => ({ run: vi.fn(), isPending: false, error: undefined }),
  useTriggerScore: () => ({ run: vi.fn(), isPending: false, error: undefined }),
  useUploadProgress: () => ({ total: 0, done: 0, failed: 0, stoppedReason: null }),
  useScoreProgress: () => ({ total: 0, done: 0, failed: 0, stoppedReason: null }),
}));

describe("module scaffolds", () => {
  it("Intake renders inside the console shell when the gate is held", () => {
    perm.allow = true;
    renderWithLocale(<IntakeWrapper />, "en");
    expect(screen.getByRole("heading", { name: "Upload applications" })).toBeInTheDocument();
    expect(screen.getByText("Upload batch")).toBeInTheDocument();
  });

  it("Intake shows the denied state when the console gate is absent", () => {
    perm.allow = false;
    renderWithLocale(<IntakeWrapper />, "en");
    expect(screen.getByText("No access")).toBeInTheDocument();
    expect(screen.queryByText("Upload batch")).not.toBeInTheDocument();
  });

  it("Journey renders its title + placeholder on the member surface", () => {
    renderWithLocale(<JourneyWrapper />, "en");
    expect(screen.getByRole("heading", { name: "Cohort journey" })).toBeInTheDocument();
    expect(screen.getByText("Not available yet")).toBeInTheDocument();
  });

  it("Community renders its title + placeholder", () => {
    renderWithLocale(<CommunityWrapper />, "en");
    expect(screen.getByRole("heading", { name: "Community hub" })).toBeInTheDocument();
  });

  it("Reports renders its title + placeholder", () => {
    renderWithLocale(<ReportsWrapper />, "en");
    expect(screen.getByRole("heading", { name: "Reports & KPIs" })).toBeInTheDocument();
  });
});
