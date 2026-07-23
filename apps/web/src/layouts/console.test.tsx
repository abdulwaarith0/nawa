import { ConsoleShell, Guard, OnboardingShell } from "@/layouts";
import { renderWithLocale } from "@/test/test-utils";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Shared, hoisted mock state for the auth + routing hooks the shells depend on.
const perm = vi.hoisted(() => ({ has: vi.fn(), isLoading: false }));
const nav = vi.hoisted(() => ({ path: "/intake" }));

vi.mock("@/hooks/Auth", () => ({
  usePermissions: () => ({ has: perm.has, isLoading: perm.isLoading, isSignedIn: true }),
}));
vi.mock("next/navigation", () => ({ usePathname: () => nav.path }));

describe("ConsoleShell", () => {
  beforeEach(() => {
    perm.has.mockReset();
    perm.isLoading = false;
    nav.path = "/intake";
  });

  it("renders the page title and only the permitted nav entries", () => {
    // Only the intake console permission is held.
    perm.has.mockImplementation((p: string) => p === "nawa:console:intake");
    renderWithLocale(<ConsoleShell title="Screening console">body</ConsoleShell>, "en");

    expect(screen.getByRole("heading", { name: "Screening console" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Intake" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Portfolio" })).not.toBeInTheDocument();
    // The whole administration section is hidden when it has no permitted items.
    expect(screen.queryByText("Administration")).not.toBeInTheDocument();
    expect(screen.getByText("Workspace")).toBeInTheDocument();
  });

  it("marks the active entry with aria-current based on the pathname", () => {
    perm.has.mockReturnValue(true);
    nav.path = "/admin/iam/groups";
    renderWithLocale(<ConsoleShell title="Groups">body</ConsoleShell>, "en");
    expect(screen.getByRole("link", { name: "Groups" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Intake" })).not.toHaveAttribute("aria-current");
  });

  it("toggles the mobile drawer open and closed", async () => {
    perm.has.mockReturnValue(true);
    const { container } = renderWithLocale(
      <ConsoleShell title="Overview">body</ConsoleShell>,
      "en",
    );
    const root = container.querySelector(".nw-console");
    expect(root).toHaveAttribute("data-open", "false");
    await userEvent.click(screen.getByRole("button", { name: "Menu" }));
    expect(root).toHaveAttribute("data-open", "true");
  });
});

describe("Guard", () => {
  beforeEach(() => {
    perm.has.mockReset();
    perm.isLoading = false;
  });
  afterEach(() => vi.clearAllMocks());

  it("shows a loading state while the session resolves", () => {
    perm.isLoading = true;
    perm.has.mockReturnValue(false);
    renderWithLocale(
      <Guard permission="nawa:iam:manage">
        <p>secret</p>
      </Guard>,
      "en",
    );
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
    expect(screen.getAllByText("Loading…").length).toBeGreaterThan(0);
  });

  it("renders a localized denied state when the permission is missing", () => {
    perm.has.mockReturnValue(false);
    renderWithLocale(
      <Guard permission="nawa:iam:manage">
        <p>secret</p>
      </Guard>,
      "en",
    );
    expect(screen.getByText("No access")).toBeInTheDocument();
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("renders children when the permission is held", () => {
    perm.has.mockReturnValue(true);
    renderWithLocale(
      <Guard permission="nawa:iam:manage">
        <p>secret</p>
      </Guard>,
      "en",
    );
    expect(screen.getByText("secret")).toBeInTheDocument();
  });
});

describe("OnboardingShell", () => {
  it("renders the localized step progress and a progressbar", () => {
    renderWithLocale(
      <OnboardingShell step={2} total={5}>
        <p>identity step</p>
      </OnboardingShell>,
      "en",
    );
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "2");
    expect(bar).toHaveAttribute("aria-valuemax", "5");
    expect(screen.getByText("Step 2 of 5")).toBeInTheDocument();
    expect(screen.getByText("identity step")).toBeInTheDocument();
  });
});
