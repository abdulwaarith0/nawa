"use client";

import { Card, EmptyState, Loading, Progress } from "@/components";
import { formatNumber } from "@/helpers/format";
import { useProgramCapacity } from "@/hooks/Dashboard/usePanels";
import { useLocale } from "@/i18n/LocaleProvider";
import { useT } from "@/i18n/useT";

// Program-capacity meters (design dashboard right rail). Fill tone escalates
// with utilisation. Data from GET /dashboard/program-capacity.
export default function ProgramCapacityPanel() {
  const t = useT("console");
  const locale = useLocale();
  const { programs, isLoading } = useProgramCapacity();

  return (
    <Card className="nw-dash-capacity">
      <div className="nw-dash-panel-head">
        <span className="nw-dash-panel-title">{t("dashboard.capacity.title")}</span>
      </div>

      {isLoading ? (
        <Loading />
      ) : !programs || programs.length === 0 ? (
        <EmptyState headline={t("dashboard.capacity.empty")} />
      ) : (
        <>
          <div className="nw-dash-capacity-legend">
            {(["filling", "nearFull", "full"] as const).map((k) => (
              <span key={k} className="nw-dash-capacity-legend-item">
                <i className={`nw-dash-cap-dot nw-dash-cap-dot--${k}`} />
                {t(`dashboard.capacity.${k}`)}
              </span>
            ))}
          </div>
          <ul className="nw-dash-capacity-list">
            {programs.map((p) => {
              const pct = p.cap > 0 ? Math.round((p.used / p.cap) * 100) : 0;
              const level = pct >= 95 ? "full" : pct >= 70 ? "nearFull" : "filling";
              const name = (locale === "ar" ? p.name_ar : p.name_en) ?? "—";
              return (
                <li key={p.program_id} className="nw-dash-capacity-row">
                  <div className="nw-dash-capacity-row-head">
                    <span className="nw-dash-capacity-name">{name}</span>
                    <span className="nw-dash-capacity-count">
                      {formatNumber(p.used, locale)}/{formatNumber(p.cap, locale)}
                    </span>
                  </div>
                  <div className="nw-dash-cap-meter" data-level={level}>
                    <Progress value={pct} label={name} />
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </Card>
  );
}
