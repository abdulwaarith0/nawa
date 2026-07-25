"use client";

import { usePermissions, useSession } from "@/hooks/Auth";
import { useCycles, useScoreProgress, useShortlist } from "@/hooks/Intake";
import { PERMISSIONS, Routes } from "@nawa/contracts";
import { useMemo } from "react";

export interface DashboardModule {
  key: "intake" | "journey" | "community" | "reports" | "admin";
  gate: string;
  href: string;
}

// Cycle statuses that represent an in-progress (not yet decided) cycle —
// matches the values actually seeded (services/api/src/nawa_api/seed_data/programs.py).
const ACTIVE_CYCLE_STATUSES = new Set(["active", "screening", "applications_open"]);

// Gates mirror what already gauges access to each destination elsewhere in
// the app (ConsoleShell's nav, homeForPermissions) — community is member-
// facing (nawa:community:read), not a console:* permission, unlike the rest.
const ALL_MODULES: DashboardModule[] = [
  { key: "intake", gate: PERMISSIONS.CONSOLE_INTAKE, href: Routes.intake.home },
  { key: "journey", gate: PERMISSIONS.CONSOLE_JOURNEY, href: Routes.journey.home },
  { key: "community", gate: PERMISSIONS.COMMUNITY_READ, href: Routes.community.home },
  { key: "reports", gate: PERMISSIONS.CONSOLE_REPORTS, href: Routes.reports.home },
  { key: "admin", gate: PERMISSIONS.CONSOLE_ADMIN, href: Routes.admin.home },
];

const RAIL_SIZE = 6;

export interface DashboardStats {
  applications: number;
  shortlisted: number;
  hiddenGems: number;
  flagged: number;
  scored: number;
  inReview: number;
  gaugePercent: number;
}

export interface DashboardRailRow {
  applicationId: string;
  applicantName: string;
  score: number | null;
  decision: string;
  hiddenGem: boolean;
}

// Composes what's already there (session, permissions, the real intake
// hooks) into a view-model for the dashboard. No new backend endpoint: the
// featured cycle's shortlist rows are the one real, already-scored dataset
// available today, so every number here is derived from them — nothing
// fabricated for sections (calendar, monthly chart, program capacity) that
// have no backing data yet.
export function useDashboard() {
  const { user, isLoading, isSignedIn } = useSession();
  const { has } = usePermissions();
  const { cycles, isLoading: cyclesLoading } = useCycles();

  const modules = useMemo(() => ALL_MODULES.filter((m) => has(m.gate)), [has]);
  const hasIntake = has(PERMISSIONS.CONSOLE_INTAKE);

  const featuredCycle = useMemo(() => {
    if (!hasIntake || !cycles || cycles.length === 0) return null;
    return cycles.find((c) => ACTIVE_CYCLE_STATUSES.has(c.status)) ?? cycles[0];
  }, [hasIntake, cycles]);

  const { rows, isLoading: rowsLoading } = useShortlist(featuredCycle?.id ?? null, {});
  const progress = useScoreProgress(featuredCycle?.id ?? null);

  const stats = useMemo<DashboardStats | null>(() => {
    if (!rows) return null;
    const applications = rows.length;
    let shortlisted = 0;
    let hiddenGems = 0;
    let flagged = 0;
    let scored = 0;
    for (const row of rows) {
      if (row.decision === "shortlist") shortlisted += 1;
      if (row.hidden_gem) hiddenGems += 1;
      const isFlagged = row.dedup_pending || row.normalize_failed;
      if (isFlagged) flagged += 1;
      else if (row.total_score !== null) scored += 1;
    }
    const inReview = applications - scored - flagged;
    const gaugePercent =
      progress.total > 0
        ? Math.round((progress.done / progress.total) * 100)
        : applications > 0
          ? Math.round((scored / applications) * 100)
          : 0;
    return { applications, shortlisted, hiddenGems, flagged, scored, inReview, gaugePercent };
  }, [rows, progress]);

  const rail = useMemo<DashboardRailRow[]>(() => {
    if (!rows) return [];
    return [...rows]
      .sort((a, b) => a.rank - b.rank)
      .slice(0, RAIL_SIZE)
      .map((row) => ({
        applicationId: row.application_id,
        applicantName: row.applicant_name,
        score: row.total_score,
        decision: row.decision,
        hiddenGem: row.hidden_gem,
      }));
  }, [rows]);

  return useMemo(
    () => ({
      user,
      isSignedIn,
      isLoading,
      modules,
      hasIntake,
      cyclesLoading: hasIntake && cyclesLoading,
      featuredCycle,
      stats,
      statsLoading: hasIntake && Boolean(featuredCycle) && rowsLoading,
      rail,
    }),
    [
      user,
      isSignedIn,
      isLoading,
      modules,
      hasIntake,
      cyclesLoading,
      featuredCycle,
      stats,
      rowsLoading,
      rail,
    ],
  );
}
