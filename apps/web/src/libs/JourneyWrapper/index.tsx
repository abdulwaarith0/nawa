"use client";

import { ComingSoon } from "@/components";
import { useT } from "@/i18n/useT";
import { TopNav } from "@/layouts";

// Cohort journey home (surface map §8, `/journey`, member view — TopNav).
// Milestone boards land in slice 07; placeholder state for now.
export default function JourneyWrapper() {
  const t = useT("console");

  return (
    <>
      <TopNav />
      <main
        style={{
          maxWidth: 960,
          marginInline: "auto",
          padding: "var(--nw-space-8) var(--nw-space-6)",
        }}
      >
        <h1 className="nw-display" style={{ fontSize: "var(--nw-text-3xl)" }}>
          {t("modules.journey.title")}
        </h1>
        <p
          style={{ color: "var(--nw-ink-600)", marginBlock: "var(--nw-space-2) var(--nw-space-6)" }}
        >
          {t("modules.journey.subtitle")}
        </p>
        <ComingSoon />
      </main>
    </>
  );
}
