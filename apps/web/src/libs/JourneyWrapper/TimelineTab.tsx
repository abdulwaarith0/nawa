"use client";

import { Badge, Button, EmptyState, Input, Loading } from "@/components";
import { useMyTimeline, useUpdateProgress } from "@/hooks/Journey";
import type { TimelineItem } from "@/hooks/Journey";
import { useProgramHistory } from "@/hooks/Profiles";
import { useLocale } from "@/i18n/LocaleProvider";
import { useT } from "@/i18n/useT";
import { useMemo, useState } from "react";

const STATUS_TONE: Record<string, "neutral" | "success" | "warning" | "danger" | "info"> = {
  not_started: "neutral",
  in_progress: "info",
  submitted: "warning",
  done: "success",
  blocked: "danger",
  waived: "neutral",
};

function TimelineRow({ item, onChanged }: { item: TimelineItem; onChanged: () => void }) {
  const t = useT("journey");
  const locale = useLocale();
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [evidenceLabel, setEvidenceLabel] = useState("");
  const update = useUpdateProgress(item.progress_id ?? "");

  const title = locale === "ar" ? item.title_ar : item.title_en;
  const description = locale === "ar" ? item.description_ar : item.description_en;

  async function advance() {
    if (!item.progress_id) return;
    const nextStatus = item.status === "not_started" ? "in_progress" : "submitted";
    await update.run({ status: nextStatus });
    onChanged();
  }

  async function addEvidence() {
    if (!item.progress_id || !evidenceUrl.trim()) return;
    await update.run({
      evidenceLinks: [
        ...item.evidence_links,
        {
          url: evidenceUrl.trim(),
          label: evidenceLabel.trim(),
          added_at: new Date().toISOString(),
        },
      ],
    });
    setEvidenceUrl("");
    setEvidenceLabel("");
    onChanged();
  }

  return (
    <li className="nw-journey-timeline-item" data-overdue={item.overdue || undefined}>
      <div className="nw-journey-timeline-node" aria-hidden="true" />
      <div className="nw-journey-timeline-body">
        <div className="nw-journey-timeline-head">
          <span className="nw-journey-timeline-title">{title}</span>
          <Badge tone={STATUS_TONE[item.status] ?? "neutral"}>{t(`status.${item.status}`)}</Badge>
        </div>
        {description ? <p className="nw-intake-subtitle">{description}</p> : null}
        {item.due_date ? (
          <p className="nw-journey-timeline-due">{t("timeline.due", { date: item.due_date })}</p>
        ) : null}

        {item.evidence_links.length > 0 ? (
          <ul className="nw-journey-timeline-evidence">
            {item.evidence_links.map((link) => (
              <li key={link.url}>
                <a href={link.url} target="_blank" rel="noreferrer">
                  {link.label || link.url}
                </a>
              </li>
            ))}
          </ul>
        ) : null}

        {item.status === "not_started" || item.status === "in_progress" ? (
          <div className="nw-journey-timeline-actions">
            <Button variant="outline" onClick={advance} loading={update.isPending}>
              {item.status === "not_started" ? t("timeline.start") : t("timeline.submit")}
            </Button>
            {item.evidence_required ? (
              <span className="nw-journey-timeline-evidence-form">
                <Input
                  placeholder={t("timeline.evidenceUrl")}
                  value={evidenceUrl}
                  onChange={(e) => setEvidenceUrl(e.target.value)}
                />
                <Input
                  placeholder={t("timeline.evidenceLabel")}
                  value={evidenceLabel}
                  onChange={(e) => setEvidenceLabel(e.target.value)}
                />
                <Button variant="ghost" onClick={addEvidence} loading={update.isPending}>
                  {t("timeline.addEvidence")}
                </Button>
              </span>
            ) : null}
          </div>
        ) : null}
      </div>
    </li>
  );
}

// Founder's own timeline (07-journey-copilot.md §2.1/§5). Resolves a cohort
// via the profiles program-history endpoint — the "which programs am I in"
// route that endpoint's own docstring says exists for exactly this.
export default function TimelineTab() {
  const t = useT("journey");
  const { history, isLoading: historyLoading, error: historyError } = useProgramHistory();

  const activeCohortId = useMemo(() => {
    if (!history) return null;
    return history.find((h) => h.status === "active")?.cohort_id ?? history[0]?.cohort_id ?? null;
  }, [history]);

  const { items, isLoading: timelineLoading, refresh } = useMyTimeline(activeCohortId);

  if (historyLoading) return <Loading />;
  if (historyError || !history || history.length === 0) {
    return (
      <EmptyState headline={t("timeline.noProfile")} description={t("timeline.noProfileBody")} />
    );
  }
  if (timelineLoading || !items) return <Loading />;
  if (items.length === 0) {
    return <EmptyState headline={t("timeline.empty")} />;
  }

  return (
    <ul className="nw-journey-timeline">
      {items.map((item) => (
        <TimelineRow key={item.milestone_id} item={item} onChanged={() => refresh()} />
      ))}
    </ul>
  );
}
