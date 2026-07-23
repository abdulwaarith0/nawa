"use client";

import { ErrorState, Loading } from "@/components";
import { EmptyState } from "@/components/States";
import { useAuditLogs } from "@/hooks/Audit";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";
import "./styles.css";

function formatWhen(iso: string): string {
  const d = new Date(iso);
  // Technical timestamps use Latin digits regardless of locale (§3.3).
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("en-GB");
}

// Audit log browser (surface map §8, `/admin/audit`, gate `nawa:audit:read`).
// Integrated against GET /audit-logs; newest first. Filters land later.
export default function AuditWrapper() {
  const t = useT("console");
  const { logs, error, isLoading, refresh } = useAuditLogs();

  let body: React.ReactNode;
  if (isLoading) {
    body = <Loading />;
  } else if (error) {
    body = <ErrorState onRetry={() => refresh()} />;
  } else if (!logs || logs.length === 0) {
    body = <EmptyState headline={t("admin.audit.empty")} />;
  } else {
    body = (
      <div style={{ overflowX: "auto" }}>
        <table className="nw-adm-table">
          <thead>
            <tr>
              <th>{t("admin.audit.columns.actor")}</th>
              <th>{t("admin.audit.columns.action")}</th>
              <th>{t("admin.audit.columns.target")}</th>
              <th>{t("admin.audit.columns.date")}</th>
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
    <ConsoleShell title={t("admin.audit.title")}>
      <Guard permission="nawa:audit:read">
        <p style={{ color: "var(--nw-ink-600)", marginBlockEnd: "var(--nw-space-4)" }}>
          {t("admin.audit.subtitle")}
        </p>
        {body}
      </Guard>
    </ConsoleShell>
  );
}
