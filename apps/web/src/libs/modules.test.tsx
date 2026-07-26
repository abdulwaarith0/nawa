import { IntakeWrapper, ReportsWrapper } from "@/libs";
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
vi.mock("next/navigation", () => ({
  usePathname: () => "/intake",
  useSearchParams: () => new URLSearchParams(),
}));

// IntakeWrapper is real (chunk 12) rather than a ComingSoon scaffold — stub
// its data hooks so this render is a pure static-shell check, same as the
// admin wrappers' own test convention.
vi.mock("@/hooks/Intake", () => ({
  useCycles: () => ({ cycles: [], error: undefined, isLoading: false, refresh: vi.fn() }),
  useUpload: () => ({ run: vi.fn(), isPending: false, error: undefined }),
  useTriggerScore: () => ({ run: vi.fn(), isPending: false, error: undefined }),
  useUploadProgress: () => ({ total: 0, done: 0, failed: 0, stoppedReason: null }),
  useScoreProgress: () => ({ total: 0, done: 0, failed: 0, stoppedReason: null }),
  useShortlist: () => ({ rows: undefined, error: undefined, isLoading: false, refresh: vi.fn() }),
}));

describe("module scaffolds", () => {
  it("Intake renders inside the console shell when the gate is held", () => {
    perm.allow = true;
    renderWithLocale(<IntakeWrapper />, "en");
    expect(screen.getAllByText("Upload batch").length).toBeGreaterThan(0);
    // No cycle is selected yet (none in the list, no ?cycle= param) — the
    // picker gate shows instead of the dropzone.
    expect(screen.getByLabelText("Cycle")).toBeInTheDocument();
  });

  it("Intake shows the denied state when the console gate is absent", () => {
    perm.allow = false;
    renderWithLocale(<IntakeWrapper />, "en");
    expect(screen.getByText("No access")).toBeInTheDocument();
    expect(screen.queryByLabelText("Cycle")).not.toBeInTheDocument();
  });

  it("Reports renders its title + placeholder", () => {
    renderWithLocale(<ReportsWrapper />, "en");
    expect(screen.getByRole("heading", { name: "Reports & KPIs" })).toBeInTheDocument();
  });
});
