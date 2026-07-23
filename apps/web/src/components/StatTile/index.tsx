"use client";

import { formatNumber } from "@/helpers/format";
import { useLocale } from "@/i18n/LocaleProvider";
import type { TLocale } from "@nawa/contracts";
import { useMemo } from "react";
import "./styles.css";

export interface IProps {
  label: string;
  value: number;
  unit?: string;
  deltaPct?: number | null;
}

// .nw-stat — label + value (display face, Latin digits) + optional delta in a
// semantic colour (§9). Numbers always render via formatNumber (numeral policy).
export default function StatTile({ label, value, unit, deltaPct }: IProps) {
  const locale: TLocale = useLocale();
  const deltaTone = deltaPct == null ? "none" : deltaPct >= 0 ? "up" : "down";

  return useMemo(
    () => (
      <div className="nw-stat">
        <span className="nw-stat-label">{label}</span>
        <span className="nw-stat-value nw-display" lang={locale}>
          {formatNumber(value, locale)}
          {unit ? <span className="nw-stat-unit"> {unit}</span> : null}
        </span>
        {deltaPct != null ? (
          <span className="nw-stat-delta" data-tone={deltaTone}>
            {deltaPct >= 0 ? "▲" : "▼"} {formatNumber(Math.abs(deltaPct), locale)}%
          </span>
        ) : null}
      </div>
    ),
    [label, value, unit, deltaPct, locale, deltaTone],
  );
}
