"use client";

import { Badge, Card, ErrorState, Loading } from "@/components";
import { EmptyState } from "@/components/States";
import { usePolicies } from "@/hooks/Iam";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";

// IAM policies (surface map §8, `/admin/iam/policies`, gate `nawa:iam:manage`).
// Integrated against GET /iam/policies; managed built-ins are flagged read-only.
export default function IamPoliciesWrapper() {
  const t = useT("console");
  const { policies, error, isLoading, refresh } = usePolicies();

  let body: React.ReactNode;
  if (isLoading) {
    body = <Loading />;
  } else if (error) {
    body = <ErrorState onRetry={() => refresh()} />;
  } else if (!policies || policies.length === 0) {
    body = <EmptyState headline={t("admin.iam.policies.empty")} />;
  } else {
    body = (
      <div style={{ display: "grid", gap: "var(--nw-space-3)" }}>
        {policies.map((p) => (
          <Card key={p.id}>
            <div
              style={{ display: "flex", justifyContent: "space-between", gap: "var(--nw-space-3)" }}
            >
              <h3 className="nw-display" style={{ fontSize: "var(--nw-text-lg)" }}>
                <bdi>{p.name}</bdi>
              </h3>
              {p.managed ? <Badge tone="neutral">{t("admin.iam.policies.builtin")}</Badge> : null}
            </div>
            {p.description ? (
              <p style={{ color: "var(--nw-ink-600)", marginBlockStart: "var(--nw-space-1)" }}>
                <bdi>{p.description}</bdi>
              </p>
            ) : null}
          </Card>
        ))}
      </div>
    );
  }

  return (
    <ConsoleShell title={t("admin.iam.policies.title")}>
      <Guard permission="nawa:iam:manage">
        <p style={{ color: "var(--nw-ink-600)", marginBlockEnd: "var(--nw-space-4)" }}>
          {t("admin.iam.policies.subtitle")}
        </p>
        {body}
      </Guard>
    </ConsoleShell>
  );
}
