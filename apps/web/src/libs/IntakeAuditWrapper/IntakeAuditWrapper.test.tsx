import IntakeAuditWrapper from "@/libs/IntakeAuditWrapper";
import { renderWithLocale } from "@/test/test-utils";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Tabs (§9) renders every tabpanel's content in the DOM at once, hiding
// inactive ones via the `hidden` attribute rather than unmounting them — so
// a row that appears in both "All entries" and a category tab exists twice
// in the DOM. Query role-based (role queries respect `hidden` by default)
// and scope text assertions to the one visible panel.
function visiblePanel() {
  return screen.getByRole("tabpanel");
}

const s = vi.hoisted(() => ({
  audit: { logs: undefined, error: undefined, isLoading: false, refresh: vi.fn() } as {
    logs: Array<Record<string, unknown>> | undefined;
    error: unknown;
    isLoading: boolean;
    refresh: () => void;
  },
}));

vi.mock("@/hooks/Audit", () => ({ useIntakeAuditLogs: () => s.audit }));
vi.mock("@/hooks/Auth", () => ({
  usePermissions: () => ({ has: () => true, isLoading: false, isSignedIn: true }),
  useSession: () => ({ user: null, isLoading: false, isSignedIn: false }),
}));
vi.mock("next/navigation", () => ({ usePathname: () => "/intake/audit" }));

beforeEach(() => {
  s.audit = { logs: undefined, error: undefined, isLoading: false, refresh: vi.fn() };
});

describe("IntakeAuditWrapper", () => {
  it("renders an empty state when there are no entries", () => {
    s.audit.logs = [];
    renderWithLocale(<IntakeAuditWrapper />, "en");
    expect(within(visiblePanel()).getByText("No intake audit entries yet.")).toBeInTheDocument();
  });

  it("renders a table row per audit entry, humanizing the action and surfacing the reason", () => {
    s.audit.logs = [
      {
        id: "1",
        actor_id: "u-1",
        actor_type: "user",
        action: "intake.decision.override",
        target_type: "intake_application",
        target_id: "app-1",
        status_code: 200,
        duration_ms: 12,
        metadata: { body: { reason: "Tied score, capacity forced a call.", decision: "waitlist" } },
        created_at: "2026-07-25T20:36:09Z",
      },
      {
        id: "2",
        actor_id: "u-1",
        actor_type: "user",
        action: "intake.score.run",
        target_type: "intake_cycle",
        target_id: "cycle-1",
        status_code: 202,
        duration_ms: 8,
        metadata: null,
        created_at: "2026-07-25T20:20:00Z",
      },
    ];
    renderWithLocale(<IntakeAuditWrapper />, "en");
    const panel = within(visiblePanel());
    expect(panel.getByRole("table")).toBeInTheDocument();
    expect(panel.getByText("Overrode AI ranking")).toBeInTheDocument();
    expect(panel.getByText("Triggered scoring run")).toBeInTheDocument();
    expect(panel.getByText("Tied score, capacity forced a call.")).toBeInTheDocument();
    expect(panel.getByText("Waitlisted")).toBeInTheDocument();
  });

  it("falls back to the raw action string for an unmapped action", () => {
    s.audit.logs = [
      {
        id: "1",
        actor_id: "u-1",
        actor_type: "user",
        action: "intake.something.unmapped",
        target_type: "intake_application",
        target_id: "app-1",
        status_code: 200,
        duration_ms: 12,
        metadata: null,
        created_at: "2026-07-25T20:36:09Z",
      },
    ];
    renderWithLocale(<IntakeAuditWrapper />, "en");
    expect(within(visiblePanel()).getByText("intake.something.unmapped")).toBeInTheDocument();
  });

  it("filters rows by the search box across action, reason, and target id", async () => {
    s.audit.logs = [
      {
        id: "1",
        actor_id: "u-1",
        actor_type: "user",
        action: "intake.decision.create",
        target_type: "intake_application",
        target_id: "app-1",
        status_code: 200,
        duration_ms: 12,
        metadata: { body: { reason: "Strong regional fit", decision: "shortlist" } },
        created_at: "2026-07-25T20:36:09Z",
      },
      {
        id: "2",
        actor_id: "u-1",
        actor_type: "user",
        action: "intake.score.run",
        target_type: "intake_cycle",
        target_id: "cycle-1",
        status_code: 202,
        duration_ms: 8,
        metadata: null,
        created_at: "2026-07-25T20:20:00Z",
      },
    ];
    renderWithLocale(<IntakeAuditWrapper />, "en");
    expect(within(visiblePanel()).getByText("Triggered scoring run")).toBeInTheDocument();

    const search = screen.getByPlaceholderText("Search action, reason, or ID…");
    await userEvent.type(search, "regional");

    const panel = within(visiblePanel());
    expect(panel.getByText("Recorded decision")).toBeInTheDocument();
    expect(panel.queryByText("Triggered scoring run")).not.toBeInTheDocument();
  });
});
