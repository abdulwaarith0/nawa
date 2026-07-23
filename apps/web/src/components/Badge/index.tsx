"use client";

import { type ReactNode, useMemo } from "react";
import "./styles.css";

type Tone = "neutral" | "success" | "warning" | "danger" | "info";

export interface IProps {
  tone?: Tone;
  icon?: ReactNode;
  children: ReactNode;
}

// .nw-badge — semantic variants use *-100 bg + *-700 text. The AI badge is a
// separate component (never here), keeping the amber rule intact (§9).
export default function Badge({ tone = "neutral", icon, children }: IProps) {
  return useMemo(
    () => (
      <span className="nw-badge" data-tone={tone}>
        {icon}
        {children}
      </span>
    ),
    [tone, icon, children],
  );
}
