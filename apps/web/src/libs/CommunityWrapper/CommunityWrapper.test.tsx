import CommunityWrapper from "@/libs/CommunityWrapper";
import { renderWithLocale } from "@/test/test-utils";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Matches CommunityWrapper's own debounce constant.
const DEBOUNCE_MS = 300;

const s = vi.hoisted(() => ({
  members: undefined as Array<Record<string, unknown>> | undefined,
  error: undefined as unknown,
  isLoading: false,
  lastFilters: undefined as unknown,
}));

vi.mock("@/hooks/Community", () => ({
  useDirectory: (filters: unknown) => {
    s.lastFilters = filters;
    return { members: s.members, error: s.error, isLoading: s.isLoading };
  },
}));
vi.mock("@/hooks/Auth", () => ({
  usePermissions: () => ({ has: () => true, isLoading: false, isSignedIn: true }),
  useSession: () => ({ user: null, isLoading: false, isSignedIn: false }),
}));
vi.mock("next/navigation", () => ({ usePathname: () => "/community" }));

beforeEach(() => {
  s.members = undefined;
  s.error = undefined;
  s.isLoading = false;
  s.lastFilters = undefined;
});

const member = (over: Partial<Record<string, unknown>> = {}) => ({
  id: "p-1",
  handle: "sara",
  display_name_ar: null,
  display_name_en: "Sara Al-Mansoori",
  headline_ar: null,
  headline_en: null,
  venture_name_ar: null,
  venture_name_en: "GreenLeaf",
  sector: "AgriTech",
  country: "QA",
  stage: "pilot",
  skills: ["CAD", "Prototyping"],
  domains: [],
  is_mentor_eligible: false,
  ...over,
});

describe("CommunityWrapper", () => {
  it("renders an empty state when no members match", () => {
    s.members = [];
    renderWithLocale(<CommunityWrapper />, "en");
    expect(screen.getByText("No members match these filters.")).toBeInTheDocument();
  });

  it("renders a card per member with venture, stage, and skills", () => {
    s.members = [member()];
    renderWithLocale(<CommunityWrapper />, "en");
    expect(screen.getByText("Sara Al-Mansoori")).toBeInTheDocument();
    expect(screen.getByText("GreenLeaf")).toBeInTheDocument();
    // "Pilot" also appears as a <option> in the stage filter Select — scope
    // to the badge specifically.
    expect(screen.getByText("Pilot", { selector: ".nw-badge" })).toBeInTheDocument();
    expect(screen.getByText("CAD")).toBeInTheDocument();
  });

  it("shows the mentor badge only for mentor-eligible members", () => {
    s.members = [member({ is_mentor_eligible: true })];
    renderWithLocale(<CommunityWrapper />, "en");
    expect(screen.getByText("Mentor")).toBeInTheDocument();
  });

  it("debounces the search box before it reaches the hook", async () => {
    s.members = [];
    renderWithLocale(<CommunityWrapper />, "en");

    const search = screen.getByPlaceholderText("Search by name, venture, or skill…");
    await userEvent.type(search, "sara");
    expect((s.lastFilters as { q?: string }).q).toBeUndefined();

    await waitFor(() => expect((s.lastFilters as { q?: string }).q).toBe("sara"), {
      timeout: DEBOUNCE_MS + 500,
    });
  });

  it("toggles the mentors-only filter", async () => {
    s.members = [];
    renderWithLocale(<CommunityWrapper />, "en");
    await userEvent.click(screen.getByLabelText("Mentors only"));
    expect((s.lastFilters as { mentors?: boolean }).mentors).toBe(true);
  });
});
