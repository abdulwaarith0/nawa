"use client";

import { type ReactNode, useMemo } from "react";
import "./styles.css";

export interface IProps {
  value: number;
  children?: ReactNode;
}

const CX = 140;
const CY = 125;
const R_IN = 76;
const R_OUT = 110;
const TICK_COUNT = 24;

interface Tick {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  tone: "filled" | "filled-leading" | "empty" | "empty-trailing";
}

function buildTicks(value: number): Tick[] {
  const filled = Math.round((Math.min(100, Math.max(0, value)) / 100) * TICK_COUNT);
  return Array.from({ length: TICK_COUNT }, (_, i) => {
    const angle = ((155 + (i / (TICK_COUNT - 1)) * 230) * Math.PI) / 180;
    const on = i < filled;
    let tone: Tick["tone"];
    if (on) tone = i >= filled - 3 ? "filled-leading" : "filled";
    else tone = i >= TICK_COUNT - 3 ? "empty-trailing" : "empty";
    return {
      x1: CX + R_IN * Math.cos(angle),
      y1: CY + R_IN * Math.sin(angle),
      x2: CX + R_OUT * Math.cos(angle),
      y2: CY + R_OUT * Math.sin(angle),
      tone,
    };
  });
}

// 24-tick semicircular gauge (ported from the approved design's GaugeRing,
// packages/ui/src/components/product.tsx) — used for the intake screening-
// progress dial. Tick geometry is computed per-render (real SVG coordinates,
// not styling), so it's the one legitimate case for inline attributes here.
export default function GaugeRing({ value, children }: IProps) {
  const ticks = useMemo(() => buildTicks(value), [value]);

  return (
    <div className="nw-gauge">
      <svg
        className="nw-gauge-svg"
        viewBox="0 0 280 180"
        role="img"
        aria-label={`${value}% complete`}
      >
        {ticks.map((tick, i) => (
          <line
            key={`${tick.x1}-${tick.y1}-${i}`}
            x1={tick.x1}
            y1={tick.y1}
            x2={tick.x2}
            y2={tick.y2}
            className={`nw-gauge-tick nw-gauge-tick--${tick.tone}`}
          />
        ))}
      </svg>
      {children ? <div className="nw-gauge-content">{children}</div> : null}
    </div>
  );
}
