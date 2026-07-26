"use client";

import { EmptyState, Tabs } from "@/components";
import { usePermissions } from "@/hooks/Auth";
import { useT } from "@/i18n/useT";
import { ConsoleShell, Guard } from "@/layouts";
import { useMemo } from "react";
import BoardTab from "./BoardTab";
import TimelineTab from "./TimelineTab";
import "./styles.css";

// Journey home (07-journey-copilot.md §5, `/journey`). Deliverable A only —
// milestone tracking. The Assistant (RAG chat) and Digests tabs the design
// mock shows have no backend yet (no routes/services exist for either);
// building them now would mean fabricating a chat interface with nothing
// real behind it, so they're left out until that backend ships.
export default function JourneyWrapper() {
  const t = useT("journey");
  const { has } = usePermissions();
  const canManage = has("nawa:journey:manage");
  const canTrack = has("nawa:journey:progress");

  const items = useMemo(() => {
    const list = [];
    if (canManage) list.push({ id: "board", label: t("tabs.board"), content: <BoardTab /> });
    if (canTrack)
      list.push({ id: "timeline", label: t("tabs.timeline"), content: <TimelineTab /> });
    return list;
  }, [canManage, canTrack, t]);

  return (
    <ConsoleShell>
      <div className="nw-shell">
        <div className="nw-page-head">
          <div>
            <div className="nw-page-eyebrow">{t("eyebrow")}</div>
            <h1 className="nw-page-title">{t("title")}</h1>
            <p className="nw-page-sub">{t("subtitle")}</p>
          </div>
        </div>

        <Guard permission="nawa:console:journey">
          {items.length === 0 ? <EmptyState headline={t("noAccess")} /> : <Tabs items={items} />}
        </Guard>
      </div>
    </ConsoleShell>
  );
}
