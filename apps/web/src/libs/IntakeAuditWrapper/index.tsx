"use client";

import {
  AiAttribution,
  Badge,
  Button,
  Callout,
  Card,
  ErrorState,
  Input,
  Loading,
  Tabs,
} from "@/components";
import { EmptyState } from "@/components/States";
import { formatDate } from "@/helpers/format";
import type { AuditLog } from "@/hooks/Audit";
import { useIntakeAuditLogs } from "@/hooks/Audit";
import { useLocale } from "@/i18n/LocaleProvider";
import type { TFunction } from "@/i18n/lookup";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";
import type { TLocale } from "@nawa/contracts";
import { Routes } from "@nawa/contracts";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Download,
  Lock,
  Search,
  Sparkles,
  User,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import "./styles.css";

// Actions this app actually audits under the three intake target types
// (routes/intake.py's @audited calls + create_decision_route's manual
// create_audit_log calls) mapped to a readable i18n key. Anything unmapped
// falls back to the raw action string rather than hiding the row.
const ACTION_LABEL_KEY: Record<string, string> = {
  "intake.decision.create": "decisionCreate",
  "intake.decision.override": "decisionOverride",
  "intake.decision.accept": "decisionAccept",
  "intake.score.run": "scoreRun",
  "intake.dedup.resolve": "dedupResolve",
  "intake.upload.create": "uploadCreate",
  "intake.application.create": "applicationCreate",
  "intake.document.attach": "documentAttach",
  "intake.export.create": "exportCreate",
  "intake.eligibility.proof": "eligibilityProof",
};

const SCORING_ACTIONS = new Set(["intake.score.run", "intake.dedup.resolve"]);
const DECISION_ACTIONS = new Set([
  "intake.decision.create",
  "intake.decision.override",
  "intake.decision.accept",
]);

function extractBody(log: AuditLog): { reason?: string; decision?: string } {
  const body = log.metadata?.body;
  if (!body || typeof body !== "object") return {};
  const { reason, decision } = body as Record<string, unknown>;
  return {
    reason: typeof reason === "string" ? reason : undefined,
    decision: typeof decision === "string" ? decision : undefined,
  };
}

function matchesSearch(log: AuditLog, query: string): boolean {
  if (!query) return true;
  const { reason } = extractBody(log);
  const haystack = [log.action, log.target_id, log.actor_id, reason]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(query.toLowerCase());
}

function csvCell(value: string): string {
  return `"${value.replace(/"/g, '""')}"`;
}

// Real client-side export of whatever's currently loaded/filtered — no
// backend export endpoint exists for the audit stream, so this downloads
// exactly the rows already on screen rather than faking a server round-trip.
function downloadAuditCsv(rows: AuditLog[]): void {
  const header = ["actor", "action", "target_type", "target_id", "reason", "created_at"];
  const lines = rows.map((log) => {
    const { reason } = extractBody(log);
    return [
      log.actor_id ?? log.actor_type,
      log.action,
      log.target_type ?? "",
      log.target_id ?? "",
      reason ?? "",
      log.created_at,
    ]
      .map((cell) => csvCell(String(cell)))
      .join(",");
  });
  const csv = [header.map(csvCell).join(","), ...lines].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "intake-audit-log.csv";
  link.click();
  URL.revokeObjectURL(url);
}

// actor_type is CHECK-constrained to ('user','system','ai') at write time
// (models/identity.py). Both non-user kinds are the automated Copilot as far
// as the reader is concerned, so they share the amber sparkle treatment.
function isAutomated(log: AuditLog): boolean {
  return log.actor_type === "ai" || log.actor_type === "system";
}

// A short, stable handle for an un-resolved actor/target UUID — enough to
// distinguish rows without dumping a full 36-char id (names aren't resolvable
// here; see the wrapper comment). The full id stays available via `title`.
function shortId(id: string | null): string {
  if (!id) return "—";
  return id.length > 8 ? id.slice(0, 8) : id;
}

const PAGE_SIZE = 25;

// One tab's worth of rows: the design's card table (§ audit) with an
// AI/human-distinguished actor cell, plus client-side pagination so the full
// seed stream doesn't render as one unbounded dump.
function AuditTable({
  rows,
  t,
  locale,
}: {
  rows: AuditLog[];
  t: TFunction;
  locale: TLocale;
}) {
  const [page, setPage] = useState(0);
  const total = rows.length;

  if (total === 0) {
    return <EmptyState headline={t("audit.empty")} />;
  }

  const pageCount = Math.ceil(total / PAGE_SIZE);
  const current = Math.min(page, pageCount - 1);
  const start = current * PAGE_SIZE;
  const pageRows = rows.slice(start, start + PAGE_SIZE);

  return (
    <Card className="nw-audit-card">
      <div className="nw-audit-scroll">
        <table className="nw-audit-table">
          <thead>
            <tr>
              <th>{t("audit.columns.actor")}</th>
              <th>{t("audit.columns.action")}</th>
              <th>{t("audit.columns.target")}</th>
              <th>{t("audit.columns.reason")}</th>
              <th>{t("audit.columns.date")}</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.map((log) => {
              const { reason, decision } = extractBody(log);
              const labelKey = ACTION_LABEL_KEY[log.action];
              const actionLabel = labelKey ? t(`audit.actionLabels.${labelKey}`) : log.action;
              const ai = isAutomated(log);
              return (
                <tr key={log.id}>
                  <td>
                    <span className="nw-audit-actor">
                      {ai ? (
                        <span
                          className="nw-audit-actor-mark nw-audit-actor-mark--ai"
                          aria-hidden="true"
                        >
                          <Sparkles size={13} />
                        </span>
                      ) : (
                        <span className="nw-audit-actor-mark" aria-hidden="true">
                          <User size={14} />
                        </span>
                      )}
                      <span className="nw-audit-actor-txt">
                        <b>
                          {ai ? (
                            t("audit.actor.copilot")
                          ) : (
                            <bdi title={log.actor_id ?? undefined}>{shortId(log.actor_id)}</bdi>
                          )}
                        </b>
                        <small>{ai ? t("audit.actor.automated") : t("audit.actor.member")}</small>
                      </span>
                    </span>
                  </td>
                  <td>
                    {ai ? (
                      <AiAttribution compact>{actionLabel}</AiAttribution>
                    ) : (
                      <span className="nw-audit-action-human">{actionLabel}</span>
                    )}
                    {decision ? (
                      <span className="nw-audit-decision-badge">
                        <Badge tone="neutral">{t(`shortlist.decisionStates.${decision}`)}</Badge>
                      </span>
                    ) : null}
                  </td>
                  <td className="nw-audit-target">
                    <bdi title={log.target_id ?? undefined}>
                      {log.target_type ?? "—"}
                      {log.target_id ? ` · ${shortId(log.target_id)}` : ""}
                    </bdi>
                  </td>
                  <td className="nw-audit-reason">{reason ?? "—"}</td>
                  <td className="nw-audit-date">
                    {formatDate(log.created_at, locale, {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                      hour12: false,
                    })}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="nw-audit-foot">
        <span className="nw-audit-showing">
          {t("audit.showing", {
            from: start + 1,
            to: start + pageRows.length,
            total,
          })}
        </span>
        <span className="nw-audit-legend">
          <AiAttribution compact>{t("audit.legend.aiAction")}</AiAttribution>
          <span className="nw-audit-legend-human">
            <i />
            {t("audit.legend.human")}
          </span>
        </span>
        {pageCount > 1 ? (
          <span className="nw-audit-pager">
            <button
              type="button"
              className="nw-icon-button"
              aria-label={t("audit.prev")}
              disabled={current === 0}
              onClick={() => setPage(current - 1)}
            >
              <ChevronLeft className="nw-icon-dir" size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              className="nw-icon-button"
              aria-label={t("audit.next")}
              disabled={current >= pageCount - 1}
              onClick={() => setPage(current + 1)}
            >
              <ChevronRight className="nw-icon-dir" size={16} aria-hidden="true" />
            </button>
          </span>
        ) : null}
      </div>
    </Card>
  );
}

// Intake-scoped audit browser (`/intake/audit`, gate `nawa:audit:read`, same
// gate `/admin/audit` uses — this isn't an admin surface, it's the same
// audit stream pre-filtered to intake activity). Actor/applicant display
// names are NOT resolved here: GET /users requires nawa:iam:manage (a
// stricter permission than nawa:audit:read, so a manager/reviewer viewing
// this page may not hold it), and resolving an applicant name means an N+1
// GET .../scorecard fetch per row against a heavier, differently-permissioned
// endpoint. Both stay raw IDs until the audit log itself is extended to
// denormalize a display name at write time.
export default function IntakeAuditWrapper() {
  const t = useT("intake");
  const locale = useLocale();
  const { logs, error, isLoading, refresh } = useIntakeAuditLogs();
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    if (!logs) return null;
    return logs.filter((log) => matchesSearch(log, query));
  }, [logs, query]);

  let body: React.ReactNode;
  if (isLoading) {
    body = <Loading />;
  } else if (error) {
    body = <ErrorState onRetry={() => refresh()} />;
  } else if (!filtered) {
    body = null;
  } else {
    const scoring = filtered.filter((log) => SCORING_ACTIONS.has(log.action));
    const decisions = filtered.filter((log) => DECISION_ACTIONS.has(log.action));
    body = (
      <Tabs
        items={[
          {
            id: "all",
            label: t("audit.tabs.all"),
            content: <AuditTable rows={filtered} t={t} locale={locale} />,
          },
          {
            id: "scoring",
            label: t("audit.tabs.scoring"),
            content: <AuditTable rows={scoring} t={t} locale={locale} />,
          },
          {
            id: "decisions",
            label: t("audit.tabs.decisions"),
            content: <AuditTable rows={decisions} t={t} locale={locale} />,
          },
        ]}
      />
    );
  }

  return (
    <ConsoleShell>
      <div className="nw-shell">
        <div className="nw-page-head">
          <div>
            <div className="nw-page-eyebrow">{t("console.eyebrow")}</div>
            <h1 className="nw-page-title">{t("audit.title")}</h1>
          </div>
          <div className="nw-page-actions">
            <Badge tone="neutral">{t("audit.readOnly")}</Badge>
            <Button
              variant="outline"
              onClick={() => filtered && downloadAuditCsv(filtered)}
              disabled={!filtered || filtered.length === 0}
            >
              <Download size={15} aria-hidden="true" />
              {t("audit.exportCsv")}
            </Button>
            <Link href={Routes.intake.home} className="nw-btn nw-btn-outline">
              <ArrowLeft size={15} aria-hidden="true" />
              {t("scorecard.backToConsole")}
            </Link>
          </div>
        </div>

        <Guard permission="nawa:audit:read">
          <Callout tone="success">
            <span className="nw-audit-banner">
              <span>
                <strong>{t("audit.banner.title")}</strong> {t("audit.banner.body")}
              </span>
              <span className="nw-audit-append-only">
                <Lock size={12} aria-hidden="true" />
                {t("audit.appendOnly")}
              </span>
            </span>
          </Callout>
          <span className="nw-audit-search">
            <Search size={15} aria-hidden="true" />
            <Input
              placeholder={t("audit.search")}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </span>
          {body}
        </Guard>
      </div>
    </ConsoleShell>
  );
}
