"use client";

import { Progress } from "@/components";
import { useT } from "@/i18n/useT";
import LocaleSwitcher from "@/layouts/LocaleSwitcher";
import { Routes } from "@nawa/contracts";
import { type ReactNode, useMemo } from "react";
import "./styles.css";

export interface IProps {
  step: number;
  total: number;
  children: ReactNode;
}

// Onboarding shell (design-system §7.3): centered column, NAWA mark on top, a
// progress bar showing step n of N with a localized aria-valuetext. Fill
// direction follows reading direction (logical, handled by <Progress/>).
export default function OnboardingShell({ step, total, children }: IProps) {
  const t = useT("console");
  const progressText = useMemo(
    () => t("onboarding.progress", { current: step, total }),
    [t, step, total],
  );

  return (
    <div className="nw-onboarding">
      <header className="nw-onboarding-header">
        <a href={Routes.home} className="nw-wordmark nw-display" lang="en">
          NAWA
        </a>
        <LocaleSwitcher />
      </header>
      <main className="nw-onboarding-main">
        <div className="nw-onboarding-progress">
          <Progress
            value={step}
            max={total}
            valueText={progressText}
            label={t("onboarding.title")}
          />
          <p className="nw-onboarding-step">{progressText}</p>
        </div>
        <div className="nw-onboarding-content">{children}</div>
      </main>
    </div>
  );
}
