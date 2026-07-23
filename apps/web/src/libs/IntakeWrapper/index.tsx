"use client";

import { ComingSoon } from "@/components";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";

// Screening console home (surface map §8, `/intake`). Console shell, gated
// `nawa:console:intake`. Backend lands in slice 06 — placeholder state for now.
export default function IntakeWrapper() {
  const t = useT("console");

  return (
    <ConsoleShell title={t("modules.intake.title")}>
      <Guard permission="nawa:console:intake">
        <p style={{ color: "var(--nw-ink-600)", marginBlockEnd: "var(--nw-space-4)" }}>
          {t("modules.intake.subtitle")}
        </p>
        <ComingSoon />
      </Guard>
    </ConsoleShell>
  );
}
