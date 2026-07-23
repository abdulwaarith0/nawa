"use client";

import { useT } from "@/i18n/useT";
import { type ReactNode, useMemo } from "react";
import "./styles.css";

type Severity = "info" | "warning" | "danger";

const ICON: Record<Severity, string> = { info: "ℹ", warning: "▲", danger: "✕" };

export interface IProps {
  severity?: Severity;
  children: ReactNode;
  onDismiss?: () => void;
}

// .nw-alert — full-width severity banner (§9). Danger-red is reserved for
// HUMAN-confirmed statuses; AI anomaly severities never render as .nw-alert
// (they use the amber scale of §10.4). Not colour alone: always icon + text.
export default function Alert({ severity = "info", children, onDismiss }: IProps) {
  const t = useT("common");

  return useMemo(
    () => (
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
    ),
    [severity, children, onDismiss, t],
  );
}
