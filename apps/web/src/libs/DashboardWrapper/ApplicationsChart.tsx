"use client";

import { Card, EmptyState, Loading } from "@/components";
import { formatNumber } from "@/helpers/format";
import { type ChartRange, useApplicationsByMonth } from "@/hooks/Dashboard/usePanels";
import { useLocale } from "@/i18n/LocaleProvider";
import { useT } from "@/i18n/useT";
import { Filter } from "lucide-react";
import { useMemo, useState } from "react";

// Applications-by-month bar chart (design dashboard). Single-series, so one
// hue; the peak month is emphasised with the deeper brand green. Values come
// from GET /dashboard/applications-by-month — nothing is charted until that
// endpoint returns data.
export default function ApplicationsChart() {
  const t = useT("console");
  const locale = useLocale();
  const [range, setRange] = useState<ChartRange>("year");
  const { points, isLoading } = useApplicationsByMonth(range);

  const max = useMemo(() => {
    if (!points || points.length === 0) return 0;
    return Math.max(...points.map((p) => p.value));
  }, [points]);

  const nextRange: ChartRange = range === "year" ? "ytd" : "year";

  return (
    <Card className="nw-dash-chart">
      <div className="nw-dash-panel-head">
        <span className="nw-dash-panel-title">{t("dashboard.chart.title")}</span>
        <button
          type="button"
          className="nw-btn nw-btn-outline nw-btn-sm"
          onClick={() => setRange(nextRange)}
        >
          <Filter size={14} aria-hidden="true" />
          {t(`dashboard.chart.${range}`)}
        </button>
      </div>

      {isLoading ? (
        <Loading />
      ) : !points || points.length === 0 ? (
        <EmptyState headline={t("dashboard.chart.empty")} />
      ) : (
        <div
          className="nw-dash-bars"
          role="img"
          aria-label={t("dashboard.chart.title")}
          style={{ gridTemplateColumns: `repeat(${points.length}, minmax(0, 1fr))` }}
        >
          {points.map((p) => {
            const pct = max > 0 ? Math.round((p.value / max) * 100) : 0;
            const peak = p.value === max && max > 0;
            return (
              <div key={p.month} className="nw-dash-bar-col">
                <div className="nw-dash-bar-track">
                  <div
                    className="nw-dash-bar-fill"
                    data-peak={peak || undefined}
                    style={{ blockSize: `${pct}%` }}
                    title={`${p.month}: ${formatNumber(p.value, locale)}`}
                  />
                </div>
                <span className="nw-dash-bar-label">{p.month}</span>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
