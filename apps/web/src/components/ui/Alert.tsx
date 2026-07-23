"use client";

import { useT } from "../../i18n/useT";

type Severity = "info" | "warning" | "danger";

const ICON: Record<Severity, string> = { info: "ℹ", warning: "▲", danger: "✕" };

// .nw-alert — full-width severity banner (§9). Danger-red is reserved for
// HUMAN-confirmed statuses; AI anomaly severities never render as .nw-alert
// (they use the amber scale of §10.4). Not colour alone: always icon + text.
export function Alert({
  severity = "info",
  children,
  onDismiss,
}: {
  severity?: Severity;
  children: React.ReactNode;
  onDismiss?: () => void;
}) {
  const t = useT("common");
  return (
    <div
      className="nw-alert"
      data-severity={severity}
      role={severity === "danger" ? "alert" : "status"}
    >
      <span className="nw-alert-icon" aria-hidden="true">
        {ICON[severity]}
      </span>
      <div className="nw-alert-body">{children}</div>
      {onDismiss ? (
        <button
          type="button"
          className="nw-btn nw-btn-ghost"
          aria-label={t("actions.close")}
          onClick={onDismiss}
        >
          ✕
        </button>
      ) : null}
    </div>
  );
}
