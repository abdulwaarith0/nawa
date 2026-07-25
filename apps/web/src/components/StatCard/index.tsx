"use client";

import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { useMemo } from "react";
import "./styles.css";

export interface IProps {
  label: string;
  value: string;
  delta?: string;
  trend?: "up" | "down";
  sub?: string;
}

// Stat tile (ported from the approved design's StatCard) — a labeled value
// with an optional delta/sub line. Callers only pass delta/sub when there's
// a real comparison value to show; there's no placeholder trend here.
export default function StatCard({ label, value, delta, trend = "up", sub }: IProps) {
  const TrendIcon = useMemo(() => (trend === "down" ? ArrowDownRight : ArrowUpRight), [trend]);

  return (
    <div className="nw-stat">
      <div className="nw-stat-head">
        <span className="nw-stat-label">{label}</span>
      </div>
      <div className="nw-stat-value">{value}</div>
      {delta || sub ? (
        <div className="nw-stat-delta">
          {delta ? (
            <span className={`nw-stat-trend nw-stat-trend--${trend}`}>
              <TrendIcon size={13} aria-hidden="true" />
              {delta}
            </span>
          ) : null}
          {sub ? <span className="nw-stat-sub">{sub}</span> : null}
        </div>
      ) : null}
    </div>
  );
}
