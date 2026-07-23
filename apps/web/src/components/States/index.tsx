"use client";

import Spinner from "@/components/Spinner";
import { useT } from "@/i18n/useT";
import { type CSSProperties, type ReactNode, useMemo } from "react";
import "./styles.css";

export interface IEmptyStateProps {
  headline: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}

// .nw-empty — centered icon + localized headline + one-line explanation +
// optional primary action (§9). Empty states always carry a constructive
// next action where the user is entitled to it.
export function EmptyState({ headline, description, icon, action }: IEmptyStateProps) {
  return useMemo(
    () => (
      <div className="nw-empty" role="status">
        {icon ? (
          <div className="nw-empty-icon" aria-hidden="true">
            {icon}
          </div>
        ) : null}
        <p className="nw-empty-headline">{headline}</p>
        {description ? <p className="nw-empty-description">{description}</p> : null}
        {action ? <div className="nw-empty-action">{action}</div> : null}
      </div>
    ),
    [headline, description, icon, action],
  );
}

export interface ISkeletonProps {
  width?: number | string;
  height?: number | string;
  ariaLabel?: string;
}

// .nw-skeleton — placeholder block with a reading-direction shimmer.
export function Skeleton({ width, height = 16, ariaLabel }: ISkeletonProps) {
  const style = useMemo<CSSProperties>(
    () => ({ width, height, display: "inline-block" }),
    [width, height],
  );

  return useMemo(
    () => (
      <span
        className="nw-skeleton"
        role="status"
        aria-busy="true"
        aria-label={ariaLabel}
        style={style}
      />
    ),
    [ariaLabel, style],
  );
}

export interface IErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

// .nw-error — inline error panel with the localized message + a retry action;
// never a blank screen, never a raw stack (§9).
export function ErrorState({ message, onRetry }: IErrorStateProps) {
  const t = useT("common");

  return useMemo(
    () => (
      <div className="nw-error" role="alert">
        <p className="nw-error-message">{message ?? t("states.error")}</p>
        {onRetry ? (
          <button type="button" className="nw-btn nw-btn-secondary" onClick={onRetry}>
            {t("actions.retry")}
          </button>
        ) : null}
      </div>
    ),
    [message, onRetry, t],
  );
}

// A simple loading placeholder using the spinner + localized label.
export function Loading() {
  const t = useT("common");

  return useMemo(
    () => (
      <div className="nw-loading">
        <Spinner label={t("states.loading")} />
        <span>{t("states.loading")}</span>
      </div>
    ),
    [t],
  );
}
