import IntakeShortlistWrapper from "@/libs/IntakeShortlistWrapper";
import { renderWithLocale } from "@/test/test-utils";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/hooks/Auth", () => ({
  usePermissions: () => ({ has: () => true, isLoading: false, isSignedIn: true }),
  useSession: () => ({ user: null, isLoading: false, isSignedIn: false }),
}));
vi.mock("next/navigation", () => ({
  usePathname: () => "/intake/cycles/cycle-1",
  useRouter: () => ({ push: vi.fn() }),
}));

const row = (over: Partial<Record<string, unknown>> = {}) => ({
  rank: 1,
  application_id: "app-1",
  applicant_name: "Sara Al-Mansoori",
  title: "GreenLeaf",
  language: "en",
  country: "QA",
  total_score: 9.1,
  criteria: [],
  hidden_gem: false,
  dedup_pending: false,
  normalize_failed: false,
  status: "scored",
  decision: "undecided",
  ...over,
});

const state = vi.hoisted(() => ({
  rows: [] as ReturnType<typeof row>[],
  isLoading: false,
  error: undefined as unknown,
  lastFilters: undefined as unknown,
  refresh: vi.fn(),
}));

vi.mock("@/hooks/Intake", () => ({
  useShortlist: (_cycleId: string, filters: unknown) => {
    state.lastFilters = filters;
    return {
      rows: state.rows,
      error: state.error,
      isLoading: state.isLoading,
      refresh: state.refresh,
    };
  },
  useExport: () => ({
    run: vi.fn().mockResolvedValue({ url: "https://example.com/export.xlsx" }),
    isPending: false,
  }),
}));

const post = vi.hoisted(() => vi.fn().mockResolvedValue(undefined));
vi.mock("@/lib/apiClient", () => ({
  getApiClient: () => ({ post }),
}));

describe("IntakeShortlistWrapper", () => {
  beforeEach(() => {
    state.rows = [];
    state.isLoading = false;
    state.error = undefined;
    state.lastFilters = undefined;
    state.refresh.mockClear();
    post.mockClear();
  });

  it("renders ranked rows through the shared Table", () => {
    state.rows = [row()];
    renderWithLocale(<IntakeShortlistWrapper cycleId="cycle-1" />, "en");
    expect(screen.getByText("Sara Al-Mansoori")).toBeInTheDocument();
    expect(screen.getByText("9.1")).toBeInTheDocument();
  });

  it("shows the empty state when no rows match", () => {
    state.rows = [];
    renderWithLocale(<IntakeShortlistWrapper cycleId="cycle-1" />, "en");
    expect(screen.getByText("No applications match these filters yet.")).toBeInTheDocument();
  });

  it("requests the server-side page via limit/offset", () => {
    state.rows = [row()];
    renderWithLocale(<IntakeShortlistWrapper cycleId="cycle-1" />, "en");
    expect(state.lastFilters).toMatchObject({ limit: 25, offset: 0 });
  });

  it("filters by decision state when a tab is clicked", async () => {
    state.rows = [row()];
    const user = userEvent.setup();
    renderWithLocale(<IntakeShortlistWrapper cycleId="cycle-1" />, "en");
    await user.click(screen.getByRole("tab", { name: "Shortlisted" }));
    expect(state.lastFilters).toMatchObject({ decision: "shortlist" });
  });

  it("blocks a bulk reject without a long-enough reason, then allows it once one is given", async () => {
    state.rows = [row()];
    const user = userEvent.setup();
    renderWithLocale(<IntakeShortlistWrapper cycleId="cycle-1" />, "en");

    await user.click(screen.getByRole("checkbox", { name: "Sara Al-Mansoori" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Decide" }), "reject");

    const submit = screen.getByRole("button", { name: "Submit decision" });
    expect(submit).toBeDisabled();

    await user.type(
      screen.getByPlaceholderText("Why this decision?"),
      "Not a fit for this cycle's focus area at all.",
    );
    await waitFor(() => expect(submit).not.toBeDisabled());
    await user.click(submit);

    expect(post).toHaveBeenCalledWith(
      "/intake/applications/app-1/decision",
      expect.objectContaining({ decision: "reject" }),
    );
  });

  it("requires a reason for a bulk shortlist too (the API can't tell client-side whether it diverges from the AI band)", async () => {
    state.rows = [row()];
    const user = userEvent.setup();
    renderWithLocale(<IntakeShortlistWrapper cycleId="cycle-1" />, "en");

    await user.click(screen.getByRole("checkbox", { name: "Sara Al-Mansoori" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Decide" }), "shortlist");

    expect(screen.getByRole("button", { name: "Submit decision" })).toBeDisabled();
    await user.type(
      screen.getByPlaceholderText("Why this decision?"),
      "Strong idea, clear market fit.",
    );
    expect(screen.getByRole("button", { name: "Submit decision" })).not.toBeDisabled();
  });

  it("disables the checkbox for an application that hasn't been scored yet", () => {
    state.rows = [row({ status: "normalized", total_score: null })];
    renderWithLocale(<IntakeShortlistWrapper cycleId="cycle-1" />, "en");
    expect(screen.getByRole("checkbox", { name: "Sara Al-Mansoori" })).toBeDisabled();
  });

  it("surfaces the real API error message when a bulk decision fails", async () => {
    state.rows = [row()];
    post.mockRejectedValueOnce(new Error("Invalid fields"));
    const user = userEvent.setup();
    renderWithLocale(<IntakeShortlistWrapper cycleId="cycle-1" />, "en");

    await user.click(screen.getByRole("checkbox", { name: "Sara Al-Mansoori" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Decide" }), "shortlist");
    await user.type(
      screen.getByPlaceholderText("Why this decision?"),
      "Strong idea, clear market fit.",
    );
    await user.click(screen.getByRole("button", { name: "Submit decision" }));

    expect(await screen.findByText("1 decision(s) failed: Invalid fields")).toBeInTheDocument();
  });
});
