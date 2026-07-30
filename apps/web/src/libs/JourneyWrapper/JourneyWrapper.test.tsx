import JourneyWrapper from "@/libs/JourneyWrapper";
import { renderWithLocale } from "@/test/test-utils";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const perm = vi.hoisted(() => ({ manage: false, track: false }));

const s = vi.hoisted(() => ({
  cycles: { cycles: undefined, error: undefined, isLoading: false, refresh: vi.fn() } as {
    cycles: Array<Record<string, unknown>> | undefined;
    error: unknown;
    isLoading: boolean;
    refresh: () => void;
  },
  cohorts: { cohorts: undefined, error: undefined, isLoading: false } as {
    cohorts: Array<Record<string, unknown>> | undefined;
    error: unknown;
    isLoading: boolean;
  },
  board: { board: undefined, error: undefined, isLoading: false, refresh: vi.fn() } as {
    board: Record<string, unknown> | undefined;
    error: unknown;
    isLoading: boolean;
    refresh: () => void;
  },
  atRisk: { atRisk: [] as Array<Record<string, unknown>>, refresh: vi.fn() },
  journeyCohorts: { cohorts: [] as Array<Record<string, unknown>>, error: undefined, isLoading: false },
  history: { history: undefined, error: undefined, isLoading: false } as {
    history: Array<Record<string, unknown>> | undefined;
    error: unknown;
    isLoading: boolean;
  },
  timeline: { items: undefined, error: undefined, isLoading: false, refresh: vi.fn() } as {
    items: Array<Record<string, unknown>> | undefined;
    error: unknown;
    isLoading: boolean;
    refresh: () => void;
  },
  review: vi.fn(),
  updateProgress: vi.fn(),
}));

vi.mock("@/hooks/Auth", () => ({
  usePermissions: () => ({
    has: (permission: string) =>
      permission === "nawa:journey:manage"
        ? perm.manage
        : permission === "nawa:journey:progress"
          ? perm.track
          : permission === "nawa:console:journey",
    isLoading: false,
    isSignedIn: true,
  }),
  useSession: () => ({ user: null, isLoading: false, isSignedIn: false }),
}));
vi.mock("next/navigation", () => ({ usePathname: () => "/journey" }));
vi.mock("@/hooks/Intake", () => ({
  useCycles: () => s.cycles,
  useCohorts: () => s.cohorts,
}));
vi.mock("@/hooks/Journey", () => ({
  useCohortBoard: () => s.board,
  useAtRisk: () => s.atRisk,
  useMyTimeline: () => s.timeline,
  useReviewProgress: () => ({ run: s.review, isPending: false, error: undefined }),
  useUpdateProgress: () => ({ run: s.updateProgress, isPending: false, error: undefined }),
  useJourneyCohorts: () => s.journeyCohorts,
  useJourneyAssistant: () => ({ messages: [], isSending: false, send: vi.fn(), reset: vi.fn() }),
}));
vi.mock("@/hooks/Profiles", () => ({
  useProgramHistory: () => s.history,
}));

beforeEach(() => {
  perm.manage = false;
  perm.track = false;
  s.cycles = { cycles: undefined, error: undefined, isLoading: false, refresh: vi.fn() };
  s.cohorts = { cohorts: undefined, error: undefined, isLoading: false };
  s.board = { board: undefined, error: undefined, isLoading: false, refresh: vi.fn() };
  s.atRisk = { atRisk: [], refresh: vi.fn() };
  s.journeyCohorts = { cohorts: [], error: undefined, isLoading: false };
  s.history = { history: undefined, error: undefined, isLoading: false };
  s.timeline = { items: undefined, error: undefined, isLoading: false, refresh: vi.fn() };
  s.review.mockReset();
  s.updateProgress.mockReset();
});

describe("JourneyWrapper", () => {
  it("renders no-access state when the session holds neither journey permission", () => {
    renderWithLocale(<JourneyWrapper />, "en");
    expect(screen.getByText("You don't have access to any Journey view yet.")).toBeInTheDocument();
  });

  it("shows the Overview + Board tabs for a manager without progress access", () => {
    perm.manage = true;
    renderWithLocale(<JourneyWrapper />, "en");
    expect(screen.getByRole("tab", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Board" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "My timeline" })).not.toBeInTheDocument();
  });

  it("shows only the My timeline tab for a founder without manage access", () => {
    perm.track = true;
    renderWithLocale(<JourneyWrapper />, "en");
    expect(screen.queryByRole("tab", { name: "Board" })).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "My timeline" })).toBeInTheDocument();
  });

  it("board: renders an empty state when no cohort has been admitted yet", async () => {
    perm.manage = true;
    s.cycles.cycles = [{ id: "cycle-1", status: "active" }];
    s.cohorts.cohorts = [];
    renderWithLocale(<JourneyWrapper />, "en");
    await userEvent.click(screen.getByRole("tab", { name: "Board" }));
    expect(screen.getByText("No cohort to track yet")).toBeInTheDocument();
  });

  it("board: renders the grid and opens the review drawer on a cell click", async () => {
    perm.manage = true;
    s.cycles.cycles = [{ id: "cycle-1", status: "active" }];
    s.cohorts.cohorts = [{ id: "cohort-1" }];
    s.board.board = {
      milestones: [{ id: "m-1", sequence: 1, title_en: "Prototype", title_ar: "نموذج" }],
      members: [
        {
          cohort_member_id: "cm-1",
          founder_profile_id: "fp-1",
          display_name_en: "Sara Al-Mansoori",
          display_name_ar: null,
          handle: "sara",
        },
      ],
      cells: [
        {
          milestone_id: "m-1",
          cohort_member_id: "cm-1",
          progress_id: "p-1",
          status: "submitted",
          overdue: false,
          evidence_links: [],
        },
      ],
    };
    renderWithLocale(<JourneyWrapper />, "en");
    await userEvent.click(screen.getByRole("tab", { name: "Board" }));

    expect(screen.getByText("Prototype")).toBeInTheDocument();
    expect(screen.getByText("Sara Al-Mansoori")).toBeInTheDocument();

    await userEvent.click(screen.getByText("Submitted"));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveTextContent("Sara Al-Mansoori · Prototype");
  });

  it("board: requires a note before accepting a block/waive review", async () => {
    perm.manage = true;
    s.cycles.cycles = [{ id: "cycle-1", status: "active" }];
    s.cohorts.cohorts = [{ id: "cohort-1" }];
    s.board.board = {
      milestones: [{ id: "m-1", sequence: 1, title_en: "Prototype", title_ar: "نموذج" }],
      members: [
        {
          cohort_member_id: "cm-1",
          founder_profile_id: "fp-1",
          display_name_en: "Sara",
          display_name_ar: null,
          handle: "sara",
        },
      ],
      cells: [
        {
          milestone_id: "m-1",
          cohort_member_id: "cm-1",
          progress_id: "p-1",
          status: "submitted",
          overdue: false,
          evidence_links: [],
        },
      ],
    };
    renderWithLocale(<JourneyWrapper />, "en");
    await userEvent.click(screen.getByRole("tab", { name: "Board" }));
    await userEvent.click(screen.getByText("Submitted"));
    await userEvent.click(screen.getByRole("button", { name: "Block" }));

    expect(s.review).not.toHaveBeenCalled();
    expect(screen.getByText("A note is required for this action.")).toBeInTheDocument();
  });

  it("timeline: renders a no-profile empty state when program history 404s", () => {
    perm.track = true;
    s.history.error = new Error("not found");
    renderWithLocale(<JourneyWrapper />, "en");
    expect(screen.getByText("No Founder Profile yet")).toBeInTheDocument();
  });

  it("timeline: renders milestone items and advances status", async () => {
    perm.track = true;
    s.history.history = [{ cohort_id: "cohort-1", status: "active" }];
    s.timeline.items = [
      {
        milestone_id: "m-1",
        sequence: 1,
        title_en: "Prototype",
        title_ar: null,
        description_en: null,
        description_ar: null,
        due_date: null,
        evidence_required: false,
        progress_id: "p-1",
        status: "not_started",
        note_ar: null,
        note_en: null,
        evidence_links: [],
        overdue: false,
      },
    ];
    renderWithLocale(<JourneyWrapper />, "en");

    expect(screen.getByText("Prototype")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(s.updateProgress).toHaveBeenCalledWith({ status: "in_progress" });
  });
});
