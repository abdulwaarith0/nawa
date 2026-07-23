"use client";

import { type ReactNode, useMemo } from "react";
import "./styles.css";

type Tone = "info" | "success";

const ICON: Record<Tone, string> = { info: "ℹ", success: "✓" };

export interface IProps {
  tone?: Tone;
  children: ReactNode;
}

// .nw-callout — static informational panel (§9). Never dismissible, never amber.
export default function Callout({ tone = "info", children }: IProps) {
  return useMemo(
    () => (
      <div className="nw-callout" data-tone={tone} role="note">
        <span className="nw-callout-icon" aria-hidden="true">
          {ICON[tone]}
        </span>
        <div>{children}</div>
      </div>
    ),
    [tone, children],
  );
}
