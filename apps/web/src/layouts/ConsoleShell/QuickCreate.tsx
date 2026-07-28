"use client";

import { usePermissions } from "@/hooks/Auth";
import { useT } from "@/i18n/useT";
import { Routes } from "@nawa/contracts";
import { ClipboardList, FileBarChart, Plus, Upload, Users } from "lucide-react";
import Link from "next/link";
import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";

interface QuickAction {
  key: string;
  href: string;
  gate: string;
  icon: ReactNode;
}

// Quick-create menu (design AppShell "＋ New"): navigation-only shortcuts, each
// gated by the same permission that guards its destination — so the menu never
// offers an action the API would reject. No notification bell ships alongside
// it: there is no notifications backend, and a decorative bell would fake data
// the same way the dashboard deliberately refuses to.
const ACTIONS: QuickAction[] = [
  {
    key: "uploadBatch",
    href: Routes.intake.upload,
    gate: "nawa:console:intake",
    icon: <Upload size={16} aria-hidden="true" />,
  },
  {
    key: "generateReport",
    href: Routes.reports.generate,
    gate: "nawa:console:reports",
    icon: <FileBarChart size={16} aria-hidden="true" />,
  },
  {
    key: "communityRequest",
    href: Routes.community.requests,
    gate: "nawa:community:read",
    icon: <Users size={16} aria-hidden="true" />,
  },
];

export default function QuickCreate() {
  const t = useT("console");
  const { has } = usePermissions();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const actions = ACTIONS.filter((a) => has(a.gate));

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onClick);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  // Nothing to create → no button (a Founder with none of these permissions).
  if (actions.length === 0) return null;

  return (
    <div className="nw-quick-create" ref={ref}>
      <button
        type="button"
        className="nw-btn nw-btn-primary nw-quick-create-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <Plus size={15} strokeWidth={2.2} aria-hidden="true" />
        {t("quickCreate.label")}
      </button>
      {open ? (
        <div className="nw-quick-create-menu" role="menu">
          <div className="nw-quick-create-heading">
            <ClipboardList size={14} aria-hidden="true" />
            {t("quickCreate.heading")}
          </div>
          {actions.map((a) => (
            <Link
              key={a.key}
              href={a.href}
              role="menuitem"
              className="nw-quick-create-item"
              onClick={close}
            >
              <span className="nw-quick-create-item-icon">{a.icon}</span>
              <span className="nw-quick-create-item-txt">
                <span className="nw-quick-create-item-title">{t(`quickCreate.${a.key}`)}</span>
                <span className="nw-quick-create-item-detail">
                  {t(`quickCreate.${a.key}Detail`)}
                </span>
              </span>
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
