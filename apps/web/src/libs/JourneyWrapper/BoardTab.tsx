"use client";

import { Avatar, Badge, Card, EmptyState, Loading } from "@/components";
import { useCohorts, useCycles } from "@/hooks/Intake";
import { useAtRisk, useCohortBoard, useReviewProgress } from "@/hooks/Journey";
import type { BoardCell, BoardMember, BoardMilestone } from "@/hooks/Journey";
import { useLocale } from "@/i18n/LocaleProvider";
import { useT } from "@/i18n/useT";
import { useMemo, useState } from "react";
import ProgressReviewDrawer from "./ProgressReviewDrawer";

const ACTIVE_CYCLE_STATUSES = new Set(["active", "screening", "applications_open"]);

const STATUS_TONE: Record<string, "neutral" | "success" | "warning" | "danger" | "info"> = {
  not_started: "neutral",
  in_progress: "info",
  submitted: "warning",
  done: "success",
  blocked: "danger",
  waived: "neutral",
};

export interface SelectedCell {
  milestone: BoardMilestone;
  member: BoardMember;
  cell: BoardCell;
}

// Program-manager board (07-journey-copilot.md §2.1/§5): milestones as
// columns, cohort members as rows. Resolves a "featured" cohort the same
// way IntakeConsoleWrapper resolves a featured cycle, then walks that
// cycle's cohorts — there is no dedicated "cohorts I manage" route, so this
// reuses the Intake domain's cycle/cohort picker rather than inventing one.
export default function BoardTab() {
  const t = useT("journey");
  const locale = useLocale();
  const { cycles, isLoading: cyclesLoading } = useCycles();

  const featuredCycle = useMemo(() => {
    if (!cycles || cycles.length === 0) return null;
    return cycles.find((c) => ACTIVE_CYCLE_STATUSES.has(c.status)) ?? cycles[0];
  }, [cycles]);

  const { cohorts, isLoading: cohortsLoading } = useCohorts(featuredCycle?.id ?? null);
  const featuredCohort = cohorts?.[0] ?? null;

  const {
    board,
    isLoading: boardLoading,
    refresh: refreshBoard,
  } = useCohortBoard(featuredCohort?.id ?? null);
  const { atRisk, refresh: refreshAtRisk } = useAtRisk(featuredCohort?.id ?? null);
  const [selected, setSelected] = useState<SelectedCell | null>(null);

  const review = useReviewProgress(selected?.cell.progress_id ?? "");

  async function handleReview(status: "done" | "blocked" | "waived", note?: string) {
    await review.run({ status, noteEn: note });
    setSelected(null);
    refreshBoard();
    refreshAtRisk();
  }

  if (cyclesLoading || cohortsLoading) return <Loading />;
  if (!featuredCohort) {
    return <EmptyState headline={t("board.noCohort")} description={t("board.noCohortBody")} />;
  }
  if (boardLoading || !board) return <Loading />;

  const milestonesByRow = [...board.milestones].sort((a, b) => a.sequence - b.sequence);
  const cellByKey = new Map(board.cells.map((c) => [`${c.milestone_id}:${c.cohort_member_id}`, c]));

  return (
    <div className="nw-split-wide nw-section-gap">
      <Card className="nw-journey-board-panel">
        {board.members.length === 0 ? (
          <EmptyState headline={t("board.noMembers")} />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="nw-journey-board">
              <thead>
                <tr>
                  <th>{t("board.columns.member")}</th>
                  {milestonesByRow.map((m) => (
                    <th key={m.id}>{locale === "ar" ? m.title_ar : m.title_en}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {board.members.map((member) => (
                  <tr key={member.cohort_member_id}>
                    <td>
                      <span className="nw-journey-board-member">
                        <Avatar
                          name={
                            (locale === "ar" ? member.display_name_ar : member.display_name_en) ??
                            member.handle
                          }
                          size={28}
                        />
                        <bdi dir="auto">
                          {(locale === "ar" ? member.display_name_ar : member.display_name_en) ??
                            member.handle}
                        </bdi>
                      </span>
                    </td>
                    {milestonesByRow.map((milestone) => {
                      const cell = cellByKey.get(`${milestone.id}:${member.cohort_member_id}`);
                      if (!cell) return <td key={milestone.id}>—</td>;
                      return (
                        <td key={milestone.id}>
                          <button
                            type="button"
                            className="nw-journey-board-cell"
                            data-overdue={cell.overdue || undefined}
                            onClick={() => setSelected({ milestone, member, cell })}
                          >
                            <Badge tone={STATUS_TONE[cell.status] ?? "neutral"}>
                              {t(`status.${cell.status}`)}
                            </Badge>
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card className="nw-journey-atrisk">
        <h3>{t("board.atRisk.title")}</h3>
        {!atRisk || atRisk.length === 0 ? (
          <p className="nw-intake-subtitle">{t("board.atRisk.empty")}</p>
        ) : (
          <ul className="nw-journey-atrisk-list">
            {atRisk.map((entry) => {
              const member = board.members.find(
                (m) => m.founder_profile_id === entry.founder_profile_id,
              );
              const milestone = board.milestones.find((m) => m.id === entry.milestone_id);
              return (
                <li key={entry.progress_id}>
                  <bdi dir="auto">
                    {member
                      ? ((locale === "ar" ? member.display_name_ar : member.display_name_en) ??
                        member.handle)
                      : entry.founder_profile_id}
                  </bdi>
                  <span className="nw-journey-atrisk-milestone">
                    {milestone ? (locale === "ar" ? milestone.title_ar : milestone.title_en) : null}
                  </span>
                  <Badge tone="danger">{t(`status.${entry.status}`)}</Badge>
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      {selected ? (
        <ProgressReviewDrawer
          milestone={selected.milestone}
          member={selected.member}
          cell={selected.cell}
          isPending={review.isPending}
          onReview={handleReview}
          onClose={() => setSelected(null)}
        />
      ) : null}
    </div>
  );
}
