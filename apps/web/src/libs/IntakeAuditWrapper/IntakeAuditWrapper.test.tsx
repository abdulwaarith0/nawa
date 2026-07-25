import IntakeAuditWrapper from "@/libs/IntakeAuditWrapper";
import { renderWithLocale } from "@/test/test-utils";
import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
    expect(screen.getByText("No intake audit entries yet.")).toBeInTheDocument();
  });

  it("renders a table row per audit entry, merged across intake target types", () => {
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
        metadata: null,
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
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("intake.decision.create")).toBeInTheDocument();
    expect(screen.getByText("intake.score.run")).toBeInTheDocument();
  });
});
