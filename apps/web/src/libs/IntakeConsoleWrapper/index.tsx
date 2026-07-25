"use client";

import {
  AiAttribution,
  Badge,
  Card,
  CriterionCard,
  EmptyState,
  Loading,
  Progress,
} from "@/components";
import { formatNumber } from "@/helpers/format";
import { usePermissions } from "@/hooks/Auth";
import { useCycles, useScorecard, useShortlist } from "@/hooks/Intake";
import { useLocale } from "@/i18n/LocaleProvider";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";
import { Routes } from "@nawa/contracts";
import Link from "next/link";
import { useMemo } from "react";
import "./styles.css";

const ACTIVE_CYCLE_STATUSES = new Set(["active", "screening", "applications_open"]);
const PREVIEW_ROWS = 6;

const DECISION_TONE: Record<string, "neutral" | "success" | "warning" | "danger" | "info"> = {
  shortlist: "success",
  accept: "success",
  waitlist: "warning",
  reject: "danger",
  decided: "info",
  undecided: "neutral",
};

// Screening console (design-system §6.3.1, `/intake` — the console landing
// page, distinct from the upload wizard which moved to `/intake/upload`).
// Scoped to one featured cycle (same pattern as the dashboard): the real
// shortlist listing has no cross-cycle "all programs" view, so — unlike the
// approved design's mixed-program mock table — every number and row here
// comes from that one cycle's real shortlist rows. There's no real "Program"
// or "Domain" field on an application, so those mock columns are dropped
// rather than fabricated; the cycle's own program/season already names the
// context in the subtitle.
export default function IntakeConsoleWrapper() {
  const t = useT("intake");
  const locale = useLocale();
  const { has } = usePermissions();
  const { cycles, isLoading: cyclesLoading } = useCycles();

  const featuredCycle = useMemo(() => {
    if (!cycles || cycles.length === 0) return null;
    return cycles.find((c) => ACTIVE_CYCLE_STATUSES.has(c.status)) ?? cycles[0];
  }, [cycles]);

  const { rows, isLoading: rowsLoading } = useShortlist(featuredCycle?.id ?? null, {});

  const stats = useMemo(() => {
    if (!rows) return null;
    const scored = rows.filter((r) => r.total_score !== null);
    const shortlisted = rows.filter((r) => r.decision === "shortlist").length;
    const inReview = rows.filter(
      (r) => r.total_score !== null && r.decision === "undecided",
    ).length;
    const avg =
      scored.length > 0
        ? scored.reduce((sum, r) => sum + (r.total_score ?? 0), 0) / scored.length
        : 0;
    return { scored: scored.length, total: rows.length, shortlisted, inReview, avg };
  }, [rows]);

  const previewRows = useMemo(() => {
    if (!rows) return [];
    return [...rows].sort((a, b) => a.rank - b.rank).slice(0, PREVIEW_ROWS);
  }, [rows]);

  const topRow = previewRows[0] ?? null;
  const { detail: featuredDetail } = useScorecard(topRow?.application_id ?? null);

  const cycleLabel = featuredCycle
    ? `${featuredCycle.program_name_en ?? featuredCycle.program_name_ar} · ${featuredCycle.name_en ?? featuredCycle.name_ar}`
    : null;

  const body = useMemo(() => {
    if (cyclesLoading) return <Loading />;
    if (!featuredCycle) {
      return (
        <EmptyState headline={t("console.noCycleTitle")} description={t("console.noCycleBody")} />
      );
    }
    if (rowsLoading || !stats) return <Loading />;

    return (
      <>
        <div className="nw-stat-grid nw-section-gap">
          <Card className="nw-console-stat">
            <span className="nw-console-stat-label">{t("console.stats.scored")}</span>
            <div className="nw-console-stat-value">{formatNumber(stats.scored, locale)}</div>
            <div className="nw-console-stat-sub">
              {t("console.stats.ofReceived", { count: formatNumber(stats.total, locale) })}
            </div>
          </Card>
          <Card className="nw-console-stat">
            <span className="nw-console-stat-label">{t("console.stats.shortlisted")}</span>
            <div className="nw-console-stat-value">{formatNumber(stats.shortlisted, locale)}</div>
          </Card>
          <Card className="nw-console-stat">
            <span className="nw-console-stat-label">{t("console.stats.inReview")}</span>
            <div className="nw-console-stat-value">{formatNumber(stats.inReview, locale)}</div>
            <div className="nw-console-stat-sub">{t("console.stats.awaitingDecision")}</div>
          </Card>
          <Card className="nw-console-stat">
            <span className="nw-console-stat-label">{t("console.stats.avgScore")}</span>
            <div className="nw-console-stat-value">
              {formatNumber(stats.avg, locale, { maximumFractionDigits: 1 })}
            </div>
          </Card>
        </div>

        <div className="nw-split-wide nw-section-gap">
          <Card className="nw-console-panel">
            {previewRows.length === 0 ? (
              <EmptyState headline={t("shortlist.empty")} />
            ) : (
              <>
                <table className="nw-console-table">
                  <thead>
                    <tr>
                      <th>{t("shortlist.columns.applicant")}</th>
                      <th>{t("console.table.score")}</th>
                      <th>{t("console.table.flags")}</th>
                      <th>{t("shortlist.columns.decision")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.map((row) => (
                      <tr key={row.application_id}>
                        <td>
                          <Link
                            href={Routes.intake.application(row.application_id)}
                            className="nw-console-row-link"
                          >
                            <bdi dir="auto">{row.applicant_name}</bdi>
                          </Link>
                        </td>
                        <td>
                          {row.total_score !== null ? (
                            <div className="nw-console-score">
                              <Progress
                                value={row.total_score}
                                max={10}
                                label={row.applicant_name}
                              />
                              <AiAttribution compact>{row.total_score.toFixed(1)}</AiAttribution>
                            </div>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td>
                          {row.hidden_gem ? (
                            <AiAttribution compact>
                              {t("shortlist.filters.flags.hiddenGem")}
                            </AiAttribution>
                          ) : row.dedup_pending ? (
                            <AiAttribution compact>
                              {t("shortlist.filters.flags.dedupPending")}
                            </AiAttribution>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td>
                          <Badge tone={DECISION_TONE[row.decision] ?? "neutral"}>
                            {t(`shortlist.decisionStates.${row.decision}`)}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="nw-console-table-footer">
                  {t("console.showing", { count: previewRows.length, total: stats.total })}{" "}
                  <Link href={Routes.intake.cycle(featuredCycle.id)}>
                    {t("console.viewFullShortlist")}
                  </Link>
                </div>
              </>
            )}
          </Card>

          {featuredDetail?.scorecard ? (
            <Card className="nw-console-panel">
              {featuredDetail.scorecard.hidden_gem ? (
                <AiAttribution compact>{t("scorecard.hiddenGem.title")}</AiAttribution>
              ) : null}
              <div className="nw-console-rail-score">{featuredDetail.scorecard.total_score}</div>
              <p className="nw-console-rail-name">
                <bdi dir="auto">{featuredDetail.application.applicant_name}</bdi> · {cycleLabel}
              </p>
              <div className="nw-console-rail-criteria">
                {featuredDetail.scorecard.criteria.map((criterion) => (
                  <CriterionCard
                    key={criterion.criterion_key}
                    criterionKey={criterion.criterion_key}
                    score={criterion.score}
                    weight={criterion.weight}
                    rationaleAr={criterion.rationale_ar}
                    rationaleEn={criterion.rationale_en}
                    citations={criterion.citations}
                    originalAnswers={featuredDetail.application.original_answers}
                    sourceLanguage={featuredDetail.application.source_language}
                  />
                ))}
              </div>
              <Link
                href={Routes.intake.application(topRow?.application_id ?? "")}
                className="nw-btn nw-btn-secondary nw-console-rail-link"
              >
                {t("console.viewScorecard")}
              </Link>
            </Card>
          ) : null}
        </div>
      </>
    );
  }, [
    cyclesLoading,
    featuredCycle,
    rowsLoading,
    stats,
    previewRows,
    featuredDetail,
    cycleLabel,
    topRow,
    locale,
    t,
  ]);

  return (
    <ConsoleShell>
      <div className="nw-shell">
        <div className="nw-page-head">
          <div>
            <div className="nw-page-eyebrow">{t("console.eyebrow")}</div>
            <h1 className="nw-page-title">{t("console.title")}</h1>
            <p className="nw-page-sub">{cycleLabel ?? t("console.subtitle")}</p>
          </div>
          <div className="nw-page-actions">
            {featuredCycle ? (
              <Link
                href={Routes.intake.cycle(featuredCycle.id)}
                className="nw-btn nw-btn-secondary"
              >
                {t("console.filters")}
              </Link>
            ) : null}
            {has("nawa:audit:read") ? (
              <Link href={Routes.intake.audit} className="nw-btn nw-btn-secondary">
                {t("console.auditLog")}
              </Link>
            ) : null}
            <Link
              href={
                featuredCycle
                  ? `${Routes.intake.upload}?cycle=${featuredCycle.id}`
                  : Routes.intake.upload
              }
              className="nw-btn nw-btn-primary"
            >
              {t("upload.title")}
            </Link>
          </div>
        </div>

        <Guard permission="nawa:console:intake">{body}</Guard>
      </div>
    </ConsoleShell>
  );
}
