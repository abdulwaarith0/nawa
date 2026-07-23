"use client";

import { Badge, Card, ErrorState, Loading } from "@/components";
import { EmptyState } from "@/components/States";
import { useGroups } from "@/hooks/Iam";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";

// IAM groups (surface map §8, `/admin/iam/groups`, gate `nawa:iam:manage`).
// Integrated against GET /iam/groups; designs all five states. Full CRUD
// (statement editors) lands with the IAM admin UI slice.
export default function IamGroupsWrapper() {
  const t = useT("console");
  const { groups, error, isLoading, refresh } = useGroups();

  let body: React.ReactNode;
  if (isLoading) {
    body = <Loading />;
  } else if (error) {
    body = <ErrorState onRetry={() => refresh()} />;
  } else if (!groups || groups.length === 0) {
    body = <EmptyState headline={t("admin.iam.groups.empty")} />;
  } else {
    body = (
      <div style={{ display: "grid", gap: "var(--nw-space-3)" }}>
        {groups.map((g) => (
          <Card key={g.id}>
            <div
              style={{ display: "flex", justifyContent: "space-between", gap: "var(--nw-space-3)" }}
            >
              <h3 className="nw-display" style={{ fontSize: "var(--nw-text-lg)" }}>
                <bdi>{g.name}</bdi>
              </h3>
              {g.managed ? <Badge tone="neutral">{t("admin.iam.policies.builtin")}</Badge> : null}
            </div>
            {g.description ? (
              <p style={{ color: "var(--nw-ink-600)", marginBlockStart: "var(--nw-space-1)" }}>
                <bdi>{g.description}</bdi>
              </p>
            ) : null}
          </Card>
        ))}
      </div>
    );
  }

  return (
    <ConsoleShell title={t("admin.iam.groups.title")}>
      <Guard permission="nawa:iam:manage">
        <p style={{ color: "var(--nw-ink-600)", marginBlockEnd: "var(--nw-space-4)" }}>
          {t("admin.iam.groups.subtitle")}
        </p>
        {body}
      </Guard>
    </ConsoleShell>
  );
}
