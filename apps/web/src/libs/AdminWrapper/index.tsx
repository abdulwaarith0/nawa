"use client";

import { Card, ErrorState, Loading } from "@/components";
import { EmptyState } from "@/components/States";
import { useSiteConfig } from "@/hooks/Admin";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";
import { useMemo } from "react";
import "./styles.css";

// Platform overview (surface map §8, `/admin`, gate `nawa:console:admin`).
// Integrated against GET /admin/site-config; designs all five states.
export default function AdminWrapper() {
  const t = useT("console");
  const { config, error, isLoading, refresh } = useSiteConfig();

  const entries = useMemo(() => Object.entries(config ?? {}), [config]);

  let body: React.ReactNode;
  if (isLoading) {
    body = <Loading />;
  } else if (error) {
    body = <ErrorState onRetry={() => refresh()} />;
  } else if (entries.length === 0) {
    body = <EmptyState headline={t("admin.overview.siteConfig")} />;
  } else {
    body = (
      <Card>
        <h2 className="nw-display" style={{ fontSize: "var(--nw-text-lg)" }}>
          {t("admin.overview.siteConfig")}
        </h2>
        <dl className="nw-adm-kv">
          {entries.map(([key, value]) => (
            <div key={key} className="nw-adm-kv-row">
              <dt>{key}</dt>
              <dd>
                <bdi>{String(value)}</bdi>
              </dd>
            </div>
          ))}
        </dl>
      </Card>
    );
  }

  return (
    <ConsoleShell title={t("admin.overview.title")}>
      <Guard permission="nawa:console:admin">
        <p style={{ color: "var(--nw-ink-600)", marginBlockEnd: "var(--nw-space-4)" }}>
          {t("admin.overview.subtitle")}
        </p>
        {body}
      </Guard>
    </ConsoleShell>
  );
}
