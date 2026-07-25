"use client";

import { ErrorState, Loading } from "@/components";
import { EmptyState } from "@/components/States";
import { useIntakeAuditLogs } from "@/hooks/Audit";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";
import "../AuditWrapper/styles.css";

function formatWhen(iso: string): string {
  const d = new Date(iso);
  // Technical timestamps use Latin digits regardless of locale (§3.3).
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("en-GB");
}

// Intake-scoped audit browser (`/intake/audit`, gate `nawa:audit:read`,
// same gate the generic `/admin/audit` page uses — this isn't an admin
// surface, it's the same audit stream pre-filtered to intake activity).
export default function IntakeAuditWrapper() {
  const t = useT("intake");
  const { logs, error, isLoading, refresh } = useIntakeAuditLogs();

  let body: React.ReactNode;
  if (isLoading) {
    body = <Loading />;
  } else if (error) {
    body = <ErrorState onRetry={() => refresh()} />;
  } else if (!logs || logs.length === 0) {
    body = <EmptyState headline={t("audit.empty")} />;
  } else {
    body = (
      <div style={{ overflowX: "auto" }}>
        <table className="nw-adm-table">
          <thead>
            <tr>
              <th>{t("audit.columns.actor")}</th>
              <th>{t("audit.columns.action")}</th>
              <th>{t("audit.columns.target")}</th>
              <th>{t("audit.columns.date")}</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td>
                  <bdi>{log.actor_id ?? log.actor_type}</bdi>
                </td>
                <td>{log.action}</td>
                <td>
                  <bdi>
                    {log.target_type ?? "—"}
                    {log.target_id ? ` · ${log.target_id}` : ""}
                  </bdi>
                </td>
                <td className="nw-adm-num">{formatWhen(log.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <ConsoleShell title={t("audit.title")}>
      <Guard permission="nawa:audit:read">
        <p style={{ color: "var(--nw-ink-600)", marginBlockEnd: "var(--nw-space-4)" }}>
          {t("audit.subtitle")}
        </p>
        {body}
      </Guard>
    </ConsoleShell>
  );
}
