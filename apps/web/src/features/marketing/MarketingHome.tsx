import { Routes } from "@nawa/contracts";

// The marketing / hub landing feature module (design-system §8 surface map).
export function MarketingHome() {
  return (
    <main
      style={{
        maxWidth: 960,
        marginInline: "auto",
        padding: "var(--nw-space-16) var(--nw-space-6)",
      }}
    >
      <p
        className="nw-badge"
        data-tone="neutral"
        style={{ background: "var(--nw-teal-100)", color: "var(--nw-teal-700)" }}
      >
        نواة · NAWA
      </p>
      <h1
        className="nw-display"
        lang="ar"
        style={{ fontSize: "var(--nw-text-4xl)", marginBlock: "var(--nw-space-4)" }}
      >
        منصة ذكاء اصطناعي واحدة لكل برامج واحة قطر للعلوم والتكنولوجيا
      </h1>
      <p style={{ color: "var(--nw-ink-600)", fontSize: "var(--nw-text-lg)", maxWidth: 640 }}>
        One AI platform running the shared lifecycle behind every program — intelligent intake,
        cohort journey tracking, a community hub, and automated reporting, all on one Founder
        Profile spine.
      </p>
      <div style={{ display: "flex", gap: "var(--nw-space-3)", marginTop: "var(--nw-space-8)" }}>
        <a className="nw-btn nw-btn-primary" href={Routes.signup}>
          Apply · تقديم
        </a>
        <a className="nw-btn nw-btn-secondary" href={Routes.login}>
          Sign in · تسجيل الدخول
        </a>
        <a className="nw-btn nw-btn-ghost" href={Routes.styleguide}>
          Styleguide
        </a>
      </div>
    </main>
  );
}
