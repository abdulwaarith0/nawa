"use client";

import {
  AiAttribution,
  Avatar,
  Badge,
  Card,
  EmptyState,
  Input,
  Loading,
  Progress,
} from "@/components";
import { useCohortBoard, useJourneyAssistant, useJourneyCohorts } from "@/hooks/Journey";
import type { CohortBoard } from "@/hooks/Journey";
import { useLocale } from "@/i18n/LocaleProvider";
import { useT } from "@/i18n/useT";
import { ArrowRight } from "lucide-react";
import { useMemo, useState } from "react";

const DONE_STATES = new Set(["done", "waived"]);

type MilestoneState = "complete" | "current" | "upcoming";

interface TimelineNode {
  id: string;
  title: string;
  due: string | null;
  state: MilestoneState;
}

interface MemberRow {
  id: string;
  name: string;
  pct: number;
}

// Derive a cohort-level milestone timeline + per-member progress from the real
// board grid (milestones × members × cells). A milestone is "complete" when
// every member is done/waived; the earliest not-complete one is "current".
function deriveOverview(
  board: CohortBoard,
  locale: string,
): { timeline: TimelineNode[]; members: MemberRow[] } {
  const milestones = [...board.milestones].sort((a, b) => a.sequence - b.sequence);
  const total = milestones.length;
  const memberCount = board.members.length;

  const cellsByMilestone = new Map<string, typeof board.cells>();
  for (const cell of board.cells) {
    const list = cellsByMilestone.get(cell.milestone_id) ?? [];
    list.push(cell);
    cellsByMilestone.set(cell.milestone_id, list);
  }

  let currentAssigned = false;
  const timeline: TimelineNode[] = milestones.map((m) => {
    const cells = cellsByMilestone.get(m.id) ?? [];
    const doneCount = cells.filter((c) => DONE_STATES.has(c.status)).length;
    const allDone = memberCount > 0 && doneCount === memberCount;
    let state: MilestoneState;
    if (allDone) {
      state = "complete";
    } else if (!currentAssigned) {
      // The earliest not-yet-complete milestone is where the cohort is now.
      state = "current";
      currentAssigned = true;
    } else {
      state = "upcoming";
    }
    return {
      id: m.id,
      title: (locale === "ar" ? m.title_ar : m.title_en) ?? m.title_en ?? m.title_ar ?? "—",
      due: m.due_date,
      state,
    };
  });

  const members: MemberRow[] = board.members.map((mem) => {
    const done = board.cells.filter(
      (c) => c.cohort_member_id === mem.cohort_member_id && DONE_STATES.has(c.status),
    ).length;
    return {
      id: mem.cohort_member_id,
      name: (locale === "ar" ? mem.display_name_ar : mem.display_name_en) ?? mem.handle,
      pct: total > 0 ? Math.round((done / total) * 100) : 0,
    };
  });

  return { timeline, members };
}

// Journey overview (design "Cohort tracker"): cohort chips + milestone timeline
// + member progress, alongside the RAG assistant rail. Every number derives
// from the real cohort board; the assistant calls the real endpoint.
export default function OverviewTab() {
  const t = useT("journey");
  const locale = useLocale();
  const { cohorts, isLoading: cohortsLoading } = useJourneyCohorts();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const activeCohortId = selectedId ?? cohorts[0]?.id ?? null;
  const activeCohort = cohorts.find((c) => c.id === activeCohortId) ?? cohorts[0] ?? null;
  const { board, isLoading: boardLoading } = useCohortBoard(activeCohortId);

  const derived = useMemo(() => (board ? deriveOverview(board, locale) : null), [board, locale]);

  if (cohortsLoading) return <Loading />;
  if (cohorts.length === 0) {
    return (
      <EmptyState headline={t("overview.noCohorts")} description={t("overview.noCohortsBody")} />
    );
  }

  return (
    <div className="nw-section-gap">
      <div className="nw-journey-chips" role="group" aria-label={t("overview.milestones")}>
        {cohorts.map((c) => {
          const label = (locale === "ar" ? c.label_ar : c.label_en) ?? c.program_name_en ?? c.id;
          const active = c.id === activeCohortId;
          return (
            <button
              key={c.id}
              type="button"
              className="nw-journey-chip"
              data-active={active || undefined}
              aria-pressed={active}
              onClick={() => setSelectedId(c.id)}
            >
              {label}
            </button>
          );
        })}
      </div>

      <div className="nw-split nw-journey-overview">
        <div className="nw-journey-overview-main">
          <Card className="nw-journey-card">
            <div className="nw-journey-card-title">
              {t("overview.milestones")}
              {activeCohort?.round_en || activeCohort?.round_ar ? (
                <span className="nw-journey-card-sub">
                  {" — "}
                  {(locale === "ar" ? activeCohort.round_ar : activeCohort.round_en) ??
                    activeCohort.round_en}
                </span>
              ) : null}
            </div>
            {boardLoading || !derived ? (
              <Loading />
            ) : derived.timeline.length === 0 ? (
              <EmptyState headline={t("overview.noMilestones")} />
            ) : (
              <ol className="nw-jtimeline">
                {derived.timeline.map((node, i) => (
                  <li key={node.id} className="nw-jtimeline-item">
                    <span className="nw-jtimeline-rail" aria-hidden="true">
                      <span className={`nw-jtimeline-node nw-jtimeline-node--${node.state}`} />
                      {i < derived.timeline.length - 1 ? (
                        <span className="nw-jtimeline-line" />
                      ) : null}
                    </span>
                    <span className="nw-jtimeline-body">
                      <span className="nw-jtimeline-head">
                        <span className="nw-jtimeline-title">{node.title}</span>
                        <Badge
                          tone={
                            node.state === "complete"
                              ? "success"
                              : node.state === "current"
                                ? "info"
                                : "neutral"
                          }
                        >
                          {t(`overview.${node.state}`)}
                        </Badge>
                      </span>
                      {node.due ? (
                        <span className="nw-jtimeline-date">
                          {t("timeline.due", {
                            date: new Date(node.due).toLocaleDateString(
                              locale === "ar" ? "ar" : "en",
                              { day: "numeric", month: "short" },
                            ),
                          })}
                        </span>
                      ) : null}
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </Card>

          <Card className="nw-journey-card nw-section-gap">
            <div className="nw-journey-card-title">{t("overview.memberProgress")}</div>
            {boardLoading || !derived ? (
              <Loading />
            ) : derived.members.length === 0 ? (
              <EmptyState headline={t("overview.noMembers")} />
            ) : (
              <ul className="nw-journey-members">
                {derived.members.map((m) => (
                  <li key={m.id} className="nw-journey-member">
                    <div className="nw-journey-member-head">
                      <span className="nw-journey-member-id">
                        <Avatar name={m.name} size={28} />
                        <bdi dir="auto">{m.name}</bdi>
                      </span>
                      <span className="nw-journey-member-pct">{m.pct}%</span>
                    </div>
                    <Progress value={m.pct} label={t("overview.pctComplete", { pct: m.pct })} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <AssistantRail cohortId={activeCohortId} />
      </div>
    </div>
  );
}

// RAG assistant rail — real endpoint, amber attribution on AI answers.
function AssistantRail({ cohortId }: { cohortId: string | null }) {
  const t = useT("journey");
  const { messages, isSending, send } = useJourneyAssistant(cohortId);
  const [draft, setDraft] = useState("");

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    send(draft);
    setDraft("");
  }

  return (
    <Card className="nw-journey-assistant">
      <div className="nw-journey-assistant-head">
        <span className="nw-journey-assistant-title">{t("assistant.title")}</span>
        <AiAttribution compact>{t("assistant.badge")}</AiAttribution>
      </div>

      <div className="nw-journey-assistant-body">
        {messages.length === 0 ? (
          <p className="nw-journey-assistant-empty">{t("assistant.empty")}</p>
        ) : (
          <div className="nw-chat">
            {messages.map((m) =>
              m.role === "user" ? (
                <div key={m.id} className="nw-chat__user">
                  {m.text}
                </div>
              ) : (
                <div key={m.id} className="nw-chat__ai">
                  {m.text === "__error__" ? (
                    <span className="nw-journey-assistant-error">{t("assistant.error")}</span>
                  ) : (
                    <AiAttribution
                      how={
                        m.citations && m.citations.length > 0 ? (
                          <ul className="nw-journey-cites">
                            {m.citations.map((c) => (
                              <li key={`${c.source}:${c.page ?? ""}`}>
                                {c.source}
                                {c.page ? ` · ${c.page}` : ""}
                              </li>
                            ))}
                          </ul>
                        ) : undefined
                      }
                    >
                      {m.text}
                    </AiAttribution>
                  )}
                </div>
              ),
            )}
            {isSending ? (
              <div className="nw-chat__ai nw-journey-assistant-thinking">
                {t("assistant.thinking")}
              </div>
            ) : null}
          </div>
        )}
      </div>

      <form className="nw-journey-assistant-form" onSubmit={onSubmit}>
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={t("assistant.placeholder")}
          aria-label={t("assistant.aria")}
          disabled={!cohortId}
        />
        <button
          type="submit"
          className="nw-journey-assistant-send"
          aria-label={t("assistant.send")}
          disabled={!cohortId || isSending || draft.trim().length === 0}
        >
          <ArrowRight className="nw-icon-dir" size={17} aria-hidden="true" />
        </button>
      </form>
    </Card>
  );
}
