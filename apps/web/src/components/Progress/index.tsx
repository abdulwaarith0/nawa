"use client";

import { useMemo } from "react";
import "./styles.css";

export interface IProps {
  value: number;
  max?: number;
  valueText?: string;
  label?: string;
}

// .nw-progress — onboarding bar / milestone meter (§9). Logical fill direction
// (follows reading direction), role=progressbar with a localized aria-valuetext.
export default function Progress({ value, max = 100, valueText, label }: IProps) {
  const pct = useMemo(() => Math.max(0, Math.min(100, (value / max) * 100)), [value, max]);

  return useMemo(
    () => (
      <div
        className="nw-progress"
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-valuetext={valueText}
        aria-label={label}
      >
        <div className="nw-progress-fill" style={{ inlineSize: `${pct}%` }} />
      </div>
    ),
    [value, max, valueText, label, pct],
  );
}
