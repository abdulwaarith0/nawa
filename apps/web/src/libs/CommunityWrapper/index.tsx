"use client";

import { ComingSoon } from "@/components";
import { useT } from "@/i18n/useT";
import { TopNav } from "@/layouts";

// Community hub home (surface map §8, `/community`, TopNav). Directory/requests/
// opportunities/mentors land in slice 08; placeholder state for now.
export default function CommunityWrapper() {
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
          {t("modules.community.title")}
        </h1>
        <p
          style={{ color: "var(--nw-ink-600)", marginBlock: "var(--nw-space-2) var(--nw-space-6)" }}
        >
          {t("modules.community.subtitle")}
        </p>
        <ComingSoon />
      </main>
    </>
  );
}
