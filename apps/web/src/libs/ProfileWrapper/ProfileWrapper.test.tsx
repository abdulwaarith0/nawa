import ProfileWrapper from "@/libs/ProfileWrapper";
import { renderWithLocale } from "@/test/test-utils";
import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const s = vi.hoisted(() => ({
  profile: undefined as Record<string, unknown> | undefined,
  error: undefined as unknown,
  isLoading: false,
}));

vi.mock("@/hooks/Profiles", () => ({
  useProfile: () => ({ profile: s.profile, error: s.error, isLoading: s.isLoading }),
}));
vi.mock("@/hooks/Auth", () => ({
  usePermissions: () => ({ has: () => true, isLoading: false, isSignedIn: true }),
  useSession: () => ({ user: null, isLoading: false, isSignedIn: false }),
}));
vi.mock("next/navigation", () => ({ usePathname: () => "/profile/sara" }));

const profile = (over: Partial<Record<string, unknown>> = {}) => ({
  handle: "sara",
  display_name_ar: null,
  display_name_en: "Sara Al-Mansoori",
  headline_ar: null,
  headline_en: "Founder, GreenLeaf",
  bio_ar: null,
  bio_en: "Building affordable water-tech for smallholder farms.",
  venture_name_ar: null,
  venture_name_en: "GreenLeaf",
  venture_summary_ar: null,
  venture_summary_en: "Soil-moisture sensors for smallholder farms.",
  stage: "pilot",
  sector: "AgriTech",
  country: "QA",
  city: "Doha",
  website: null,
  links: [],
  skills: ["CAD"],
  domains: ["AgriTech"],
  is_mentor_eligible: false,
  kpi_snapshot: {},
  kpi_snapshot_at: null,
  program_history: [],
  asks: [],
  ...over,
});

beforeEach(() => {
  s.profile = undefined;
  s.error = undefined;
  s.isLoading = false;
});

describe("ProfileWrapper", () => {
  it("renders a not-found state when the profile is missing", () => {
    renderWithLocale(<ProfileWrapper handle="ghost" />, "en");
    expect(screen.getByText("Profile not found")).toBeInTheDocument();
  });

  it("renders identity, venture, and an empty KPI state", () => {
    s.profile = profile();
    renderWithLocale(<ProfileWrapper handle="sara" />, "en");
    expect(screen.getByText("Sara Al-Mansoori")).toBeInTheDocument();
    expect(screen.getByText("Founder, GreenLeaf")).toBeInTheDocument();
    expect(screen.getByText("Soil-moisture sensors for smallholder farms.")).toBeInTheDocument();
    expect(screen.getByText("No KPI data yet.")).toBeInTheDocument();
  });

  it("renders raw KPI data once the snapshot is non-empty", () => {
    s.profile = profile({ kpi_snapshot: { mrr: 1200 } });
    renderWithLocale(<ProfileWrapper handle="sara" />, "en");
    expect(screen.queryByText("No KPI data yet.")).not.toBeInTheDocument();
    expect(screen.getByText(/"mrr": 1200/)).toBeInTheDocument();
  });

  it("renders program history entries", () => {
    s.profile = profile({
      program_history: [
        {
          cohort_id: "c-1",
          cohort_name_ar: null,
          cohort_name_en: "Season 18",
          cycle_id: "cy-1",
          cycle_name_ar: null,
          cycle_name_en: "Season 18",
          program_id: "p-1",
          program_name_ar: null,
          program_name_en: "Innovation Fellowship",
          role: "member",
          status: "active",
          starts_at: "2026-01-01",
        },
      ],
    });
    renderWithLocale(<ProfileWrapper handle="sara" />, "en");
    expect(screen.getByText(/Innovation Fellowship/)).toBeInTheDocument();
    expect(screen.getByText(/Season 18/)).toBeInTheDocument();
  });

  it("only renders active asks", () => {
    s.profile = profile({
      asks: [
        { kind: "talent", text_ar: null, text_en: "Looking for a CTO", active: true },
        { kind: "intro", text_ar: null, text_en: "Old closed ask", active: false },
      ],
    });
    renderWithLocale(<ProfileWrapper handle="sara" />, "en");
    expect(screen.getByText("Looking for a CTO")).toBeInTheDocument();
    expect(screen.queryByText("Old closed ask")).not.toBeInTheDocument();
  });
});
