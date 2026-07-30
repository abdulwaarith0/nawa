"use client";

import { Card, EmptyState, Loading } from "@/components";
import { type CalendarDotKind, useCalendar } from "@/hooks/Dashboard/usePanels";
import { useLocale } from "@/i18n/LocaleProvider";
import { useT } from "@/i18n/useT";
import { useMemo, useState } from "react";

const DOT_KINDS: CalendarDotKind[] = ["screening", "interview", "deadline"];

function isoMonth(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

// Month calendar (design dashboard). Events (screening / interviews /
// deadlines) come from GET /dashboard/calendar?month=YYYY-MM as coloured dots.
export default function CalendarPanel() {
  const t = useT("console");
  const locale = useLocale();
  const [month] = useState(() => isoMonth(new Date()));
  const { calendar, isLoading } = useCalendar(month);

  const weekdays = useMemo(() => {
    const fmt = new Intl.DateTimeFormat(locale === "ar" ? "ar" : "en", { weekday: "short" });
    // Week starts Sunday (matches the design's Sun–Sat grid).
    return Array.from({ length: 7 }, (_, i) => fmt.format(new Date(2024, 8, 1 + i)));
  }, [locale]);

  const grid = useMemo(() => {
    const [y, m] = month.split("-").map(Number) as [number, number];
    const first = new Date(y, m - 1, 1);
    const daysInMonth = new Date(y, m, 0).getDate();
    const lead = first.getDay(); // 0=Sun
    const cells: Array<{ day: number | null; iso: string | null }> = [];
    for (let i = 0; i < lead; i++) cells.push({ day: null, iso: null });
    for (let d = 1; d <= daysInMonth; d++) {
      cells.push({ day: d, iso: `${month}-${String(d).padStart(2, "0")}` });
    }
    while (cells.length % 7 !== 0) cells.push({ day: null, iso: null });
    return cells;
  }, [month]);

  const kindsByDate = useMemo(() => {
    const map = new Map<string, CalendarDotKind[]>();
    for (const d of calendar?.days ?? []) map.set(d.date, d.kinds);
    return map;
  }, [calendar]);

  const monthLabel = useMemo(() => {
    const [y, m] = month.split("-").map(Number) as [number, number];
    return new Intl.DateTimeFormat(locale === "ar" ? "ar" : "en", {
      month: "long",
      year: "numeric",
    }).format(new Date(y, m - 1, 1));
  }, [month, locale]);

  return (
    <Card className="nw-dash-calendar">
      <div className="nw-dash-panel-head">
        <span className="nw-dash-panel-title">{monthLabel}</span>
      </div>

      {isLoading ? (
        <Loading />
      ) : !calendar ? (
        <EmptyState headline={t("dashboard.calendar.empty")} />
      ) : (
        <>
          <div className="nw-dash-cal-grid" role="grid" aria-label={monthLabel}>
            {weekdays.map((w) => (
              <span key={w} className="nw-dash-cal-weekday" role="columnheader">
                {w}
              </span>
            ))}
            {grid.map((cell, i) => (
              <span
                // Empty pad cells have no stable id; index key is fine as the
                // grid is fully recomputed per month.
                key={cell.iso ?? `pad-${i}`}
                className="nw-dash-cal-day"
                data-empty={cell.day === null || undefined}
                data-today={cell.iso === calendar.today || undefined}
                role="gridcell"
              >
                {cell.day !== null ? (
                  <>
                    <span className="nw-dash-cal-num">{cell.day}</span>
                    <span className="nw-dash-cal-dots">
                      {(cell.iso ? (kindsByDate.get(cell.iso) ?? []) : []).map((k) => (
                        <i key={k} className={`nw-dash-cal-dot nw-dash-cal-dot--${k}`} />
                      ))}
                    </span>
                  </>
                ) : null}
              </span>
            ))}
          </div>
          <div className="nw-dash-cal-legend">
            {DOT_KINDS.map((k) => (
              <span key={k} className="nw-dash-cal-legend-item">
                <i className={`nw-dash-cal-dot nw-dash-cal-dot--${k}`} />
                {t(
                  `dashboard.calendar.${k === "interview" ? "interviews" : k === "deadline" ? "deadlines" : "screening"}`,
                )}
              </span>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}
