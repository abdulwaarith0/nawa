"use client";

import {
  AiAttribution,
  Avatar,
  Badge,
  Card,
  EmptyState,
  GaugeRing,
  Loading,
  StatCard,
} from "@/components";
import { formatNumber } from "@/helpers/format";
import { useDashboard } from "@/hooks/Dashboard";
import type { DashboardRailRow } from "@/hooks/Dashboard/useDashboard";
import { useLocale } from "@/i18n/LocaleProvider";
import { useT } from "@/i18n/useT";
import { ConsoleShell } from "@/layouts";
import { Routes } from "@nawa/contracts";
import Link from "next/link";
import { useMemo } from "react";
import ApplicationsChart from "./ApplicationsChart";
import CalendarPanel from "./CalendarPanel";
import ProgramCapacityPanel from "./ProgramCapacityPanel";
import "./styles.css";

const DECISION_TONE: Record<string, "neutral" | "success" | "warning" | "danger" | "info"> = {
  shortlist: "success",
  accept: "success",
  waitlist: "warning",
  reject: "danger",
  decided: "info",
  undecided: "neutral",
};

// The permission-aware landing hub (`/dashboard`). Signed-out and no-module
// sessions get the honest empty states they always had; sessions without
// intake access fall back to the plain module-link grid (nothing rich exists
// for Journey/Community/Reports yet); intake holders get the real screening
// overview (design-system's approved new layout) built entirely from the
// featured cycle's shortlist rows — no fabricated deltas or unbacked panels.
export default function DashboardWrapper() {
  const t = useT("console");
  const locale = useLocale();
  const {
    user,
    isSignedIn,
    isLoading,
    modules,
    hasIntake,
    cyclesLoading,
    featuredCycle,
    stats,
    statsLoading,
    rail,
  } = useDashboard();

  const eyebrow = t("dashboard.eyebrow");
  const heading = useMemo(
    () => (user ? t("dashboard.welcome", { name: user.full_name }) : t("nav.dashboard")),
    [user, t],
  );

  const body = useMemo(() => {
    if (isLoading) return <Loading />;

    if (!isSignedIn) {
      return (
        <EmptyState
          headline={t("dashboard.signedOutTitle")}
          description={t("dashboard.signedOutBody")}
          action={
            <Link
              href={`${Routes.login}?next=${Routes.dashboard}`}
              className="nw-btn nw-btn-primary"
            >
              {t("dashboard.signIn")}
            </Link>
          }
        />
      );
    }

    if (modules.length === 0) {
      return (
        <EmptyState headline={t("dashboard.emptyTitle")} description={t("dashboard.emptyBody")} />
      );
    }

    if (!hasIntake) {
      return (
        <div className="nw-dashboard-grid">
          {modules.map((m) => (
            <Link key={m.key} href={m.href} className="nw-dashboard-card">
              <Card>
                <h2 className="nw-dashboard-card-title">{t(`modules.${m.key}.title`)}</h2>
                <p className="nw-dashboard-card-subtitle">{t(`modules.${m.key}.subtitle`)}</p>
              </Card>
            </Link>
          ))}
        </div>
      );
    }

    if (cyclesLoading) return <Loading />;

    if (!featuredCycle) {
      return (
        <EmptyState
          headline={t("dashboard.noCycleTitle")}
          description={t("dashboard.noCycleBody")}
        />
      );
    }

    if (statsLoading || !stats) return <Loading />;

    return (
      <>
        <div className="nw-stat-grid nw-section-gap">
          <StatCard
            label={t("dashboard.stats.applications")}
            value={formatNumber(stats.applications, locale)}
          />
          <StatCard
            label={t("dashboard.stats.shortlisted")}
            value={formatNumber(stats.shortlisted, locale)}
          />
          <StatCard
            label={t("dashboard.stats.hiddenGems")}
            value={formatNumber(stats.hiddenGems, locale)}
          />
          <StatCard
            label={t("dashboard.stats.flagged")}
            value={formatNumber(stats.flagged, locale)}
          />
        </div>

        <div className="nw-split nw-section-gap">
          <div>
            <div className="nw-pair-grid">
              <Card className="nw-dashboard-panel">
                <div className="nw-dashboard-panel-head">
                  <span className="nw-dashboard-panel-title">
                    {t("dashboard.screeningProgress.title")}
                  </span>
                  <Link href={Routes.intake.home}>
                    <AiAttribution compact>{t("dashboard.screeningProgress.badge")}</AiAttribution>
                  </Link>
                </div>
                <Link href={Routes.intake.home} className="nw-dashboard-gauge-link">
                  <GaugeRing value={stats.gaugePercent}>
                    <div className="nw-dashboard-gauge-value">{stats.gaugePercent}%</div>
                    <div className="nw-dashboard-gauge-sub">
                      {t("dashboard.screeningProgress.sub")}
                    </div>
                  </GaugeRing>
                </Link>
                <div className="nw-dashboard-legend">
                  <span className="nw-dashboard-legend-item">
                    <i className="nw-dashboard-legend-dot nw-dashboard-legend-dot--scored" />
                    {t("dashboard.screeningProgress.scored")} · {formatNumber(stats.scored, locale)}
                  </span>
                  <span className="nw-dashboard-legend-item">
                    <i className="nw-dashboard-legend-dot nw-dashboard-legend-dot--review" />
                    {t("dashboard.screeningProgress.inReview")} ·{" "}
                    {formatNumber(Math.max(stats.inReview, 0), locale)}
                  </span>
                  <span className="nw-dashboard-legend-item">
                    <i className="nw-dashboard-legend-dot nw-dashboard-legend-dot--flagged" />
                    {t("dashboard.screeningProgress.flagged")} ·{" "}
                    {formatNumber(stats.flagged, locale)}
                  </span>
                </div>
              </Card>

              <CalendarPanel />
            </div>

            <div className="nw-section-gap">
              <ApplicationsChart />
            </div>
          </div>

          <div>
            <Card className="nw-dashboard-panel">
              <div className="nw-dashboard-panel-head">
                <span className="nw-dashboard-panel-title">
                  {t("dashboard.rail.title")} ({formatNumber(rail.length, locale)})
                </span>
                <Link className="nw-link" href={Routes.intake.home}>
                  {t("dashboard.rail.viewAll")}
                </Link>
              </div>
              {rail.length === 0 ? (
                <p className="nw-dashboard-rail-empty">{t("dashboard.rail.empty")}</p>
              ) : (
                <div className="nw-dashboard-rail">
                  {rail.map((row: DashboardRailRow) => (
                    <Link
                      key={row.applicationId}
                      href={Routes.intake.application(row.applicationId)}
                      className="nw-dashboard-rail-row"
                    >
                      <div className="nw-dashboard-rail-row-head">
                        <Badge tone={DECISION_TONE[row.decision] ?? "neutral"}>
                          {row.decision}
                        </Badge>
                      </div>
                      <div className="nw-dashboard-rail-row-body">
                        <Avatar name={row.applicantName} size={32} />
                        <span className="nw-dashboard-rail-name" title={row.applicantName}>
                          {row.applicantName}
                        </span>
                      </div>
                      {row.score !== null ? (
                        <AiAttribution compact>
                          {t("dashboard.rail.aiScore")}{" "}
                          {formatNumber(row.score, locale, { maximumFractionDigits: 1 })}
                        </AiAttribution>
                      ) : null}
                    </Link>
                  ))}
                </div>
              )}
            </Card>

            <div className="nw-section-gap">
              <ProgramCapacityPanel />
            </div>
          </div>
        </div>
      </>
    );
  }, [
    isLoading,
    isSignedIn,
    modules,
    hasIntake,
    cyclesLoading,
    statsLoading,
    stats,
    featuredCycle,
    rail,
    locale,
    t,
  ]);

  return useMemo(
    () => (
      <ConsoleShell>
        <div className="nw-shell">
          <div className="nw-page-head">
            <div>
              <div className="nw-page-eyebrow">{eyebrow}</div>
              <h1 className="nw-page-title">{heading}</h1>
            </div>
            {hasIntake ? (
              <div className="nw-page-actions">
                <Link href={Routes.intake.home} className="nw-btn nw-btn-secondary">
                  {t("dashboard.newBatch")}
                </Link>
              </div>
            ) : null}
          </div>
          {body}
        </div>
      </ConsoleShell>
    ),
    [eyebrow, heading, hasIntake, body, t],
  );
}
