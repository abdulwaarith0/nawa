"use client";

import { Badge, Button, Textarea } from "@/components";
import type { BoardCell, BoardMember, BoardMilestone } from "@/hooks/Journey";
import { useLocale } from "@/i18n/LocaleProvider";
import { useT } from "@/i18n/useT";
import { useEffect, useState } from "react";

export interface IProps {
  milestone: BoardMilestone;
  member: BoardMember;
  cell: BoardCell;
  isPending: boolean;
  onReview: (status: "done" | "blocked" | "waived", note?: string) => void;
  onClose: () => void;
}

const NOTE_REQUIRED = new Set(["blocked", "waived"]);

// Manager review drawer (07-journey-copilot.md §2.1 board cell click): a
// note is required for blocked/waived (schema also enforces it server-side).
export default function ProgressReviewDrawer({
  milestone,
  member,
  cell,
  isPending,
  onReview,
  onClose,
}: IProps) {
  const t = useT("journey");
  const locale = useLocale();
  const [note, setNote] = useState("");
  const [pendingAction, setPendingAction] = useState<"done" | "blocked" | "waived" | null>(null);

  const memberName =
    (locale === "ar" ? member.display_name_ar : member.display_name_en) ?? member.handle;
  const milestoneTitle = locale === "ar" ? milestone.title_ar : milestone.title_en;

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  function submit(status: "done" | "blocked" | "waived") {
    if (NOTE_REQUIRED.has(status) && note.trim().length === 0) {
      setPendingAction(status);
      return;
    }
    onReview(status, note.trim() || undefined);
  }

  const noteRequired = pendingAction !== null && NOTE_REQUIRED.has(pendingAction);

  return (
    // biome-ignore lint/a11y/useKeyWithClickEvents: decorative click-outside-to-dismiss only — Esc (handled above) and the explicit close button already cover keyboard users.
    <div
      className="nw-journey-drawer-scrim"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="nw-journey-drawer"
        role="dialog"
        aria-modal="true"
        aria-label={t("board.drawer.title")}
      >
        <div className="nw-journey-drawer-head">
          <h3>{t("board.drawer.title")}</h3>
          <button
            type="button"
            className="nw-journey-drawer-close"
            onClick={onClose}
            aria-label={t("board.drawer.close")}
          >
            ×
          </button>
        </div>
        <p>
          <bdi dir="auto">{memberName}</bdi> · <bdi dir="auto">{milestoneTitle}</bdi>
        </p>
        <Badge tone="neutral">{t(`status.${cell.status}`)}</Badge>

        <div className="nw-journey-drawer-section">
          <h4>{t("board.drawer.evidence")}</h4>
          {cell.evidence_links.length === 0 ? (
            <p className="nw-intake-subtitle">{t("board.drawer.noEvidence")}</p>
          ) : (
            <ul>
              {cell.evidence_links.map((link) => (
                <li key={link.url}>
                  <a href={link.url} target="_blank" rel="noreferrer">
                    {link.label || link.url}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>

        <Textarea
          label={t("board.drawer.noteLabel")}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          error={noteRequired ? t("board.drawer.noteRequired") : undefined}
        />

        <div className="nw-journey-drawer-actions">
          <Button onClick={() => submit("done")} loading={isPending}>
            {t("board.drawer.accept")}
          </Button>
          <Button variant="outline" onClick={() => submit("blocked")} loading={isPending}>
            {t("board.drawer.block")}
          </Button>
          <Button variant="outline" onClick={() => submit("waived")} loading={isPending}>
            {t("board.drawer.waive")}
          </Button>
        </div>
      </div>
    </div>
  );
}
