"use client";

import { Badge, Button, Callout, ErrorState, Input, Loading, Tabs } from "@/components";
import { EmptyState } from "@/components/States";
import { formatDate } from "@/helpers/format";
import type { AuditLog } from "@/hooks/Audit";
import { useIntakeAuditLogs } from "@/hooks/Audit";
import { useLocale } from "@/i18n/LocaleProvider";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";
import { Routes } from "@nawa/contracts";
import { ArrowLeft, Download, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import "../AuditWrapper/styles.css";
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

  const renderTable = (rows: AuditLog[]) => {
    if (rows.length === 0) {
      return <EmptyState headline={t("audit.empty")} />;
    }
    return (
      <div style={{ overflowX: "auto" }}>
        <table className="nw-adm-table">
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
            {rows.map((log) => {
              const { reason, decision } = extractBody(log);
              const labelKey = ACTION_LABEL_KEY[log.action];
              return (
                <tr key={log.id}>
                  <td>
                    <bdi>{log.actor_id ?? log.actor_type}</bdi>
                  </td>
                  <td>
                    {labelKey ? t(`audit.actionLabels.${labelKey}`) : log.action}
                    {decision ? (
                      <span className="nw-audit-decision-badge">
                        <Badge tone="neutral">{t(`shortlist.decisionStates.${decision}`)}</Badge>
                      </span>
                    ) : null}
                  </td>
                  <td>
                    <bdi>
                      {log.target_type ?? "—"}
                      {log.target_id ? ` · ${log.target_id}` : ""}
                    </bdi>
                  </td>
                  <td>{reason ?? "—"}</td>
                  <td className="nw-adm-num">
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
    );
  };

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
          { id: "all", label: t("audit.tabs.all"), content: renderTable(filtered) },
          { id: "scoring", label: t("audit.tabs.scoring"), content: renderTable(scoring) },
          { id: "decisions", label: t("audit.tabs.decisions"), content: renderTable(decisions) },
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
            <strong>{t("audit.banner.title")}</strong> {t("audit.banner.body")}
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
